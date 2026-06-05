from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from ai_engine import vectorize_text, cosine_similarity
from routes.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/student-embedding")
async def update_student_embedding(skills: list[str], resume_text: str = "", user=Depends(get_current_user)):
    """Generate and store embedding for a student based on skills + resume"""
    if user["role"] != "student":
        raise HTTPException(403, "Only students can update their embedding")
    
    text = " ".join(skills) + " " + resume_text
    embedding = vectorize_text(text)
    
    supabase.table("users").update({
        "skills_embedding": embedding,
        "skills": skills,
        "resume_text": resume_text
    }).eq("id", user["id"]).execute()
    
    return {"message": "Embedding updated"}

@router.post("/job-embedding/{job_id}")
async def update_job_embedding(job_id: str, user=Depends(get_current_user)):
    """Generate and store embedding for a job posting"""
    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    text = job.data["title"] + " " + job.data["description"] + " " + " ".join(job.data.get("requirements", []))
    embedding = vectorize_text(text)
    
    supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
    return {"message": "Job embedding updated"}

@router.get("/recommendations/{student_id}")
async def get_recommendations(student_id: str, threshold: float = 0.6, limit: int = 20):
    """Get job recommendations for a student based on embedding similarity"""
    # Get student embedding
    student = supabase.table("users").select("skills_embedding").eq("id", student_id).eq("role", "student").single().execute()
    if not student.data or not student.data.get("skills_embedding"):
        raise HTTPException(404, "Student embedding not found. Please update your skills first.")
    
    student_vec = student.data["skills_embedding"]
    
    # Get all jobs with embeddings (only active/approved)
    jobs = supabase.table("jobs").select("*").eq("status", "approved").not_.is_("job_embedding", "null").execute()
    
    recommendations = []
    for job in jobs.data:
        score = cosine_similarity(student_vec, job["job_embedding"])
        if score >= threshold:
            # Get company name
            company = supabase.table("companies").select("name").eq("id", job["company_id"]).single().execute()
            recommendations.append({
                "job": {
                    **job,
                    "company_name": company.data["name"] if company.data else None
                },
                "match_score": round(score * 100, 2)
            })
    
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:limit]

@router.get("/recommendations/student/me")
async def get_my_recommendations(threshold: float = 0.6, user=Depends(get_current_user)):
    """Get recommendations for the currently logged-in student"""
    if user["role"] != "student":
        raise HTTPException(403, "Only students can get recommendations")
    return await get_recommendations(user["id"], threshold)