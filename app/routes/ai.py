from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text, cosine_similarity
from app.routes.auth import get_current_user

router = APIRouter()

@router.post("/student-embedding")
async def update_student_embedding(skills: list[str], resume_text: str = "", user=Depends(get_current_user)):
    if user.get("role") != "student":
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
    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    text = job.data["title"] + " " + job.data["description"] + " " + " ".join(job.data.get("requirements", []))
    embedding = vectorize_text(text)
    
    supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
    return {"message": "Job embedding updated"}

@router.get("/recommendations/{student_id}")
async def get_recommendations(
    student_id: str, 
    threshold: float = 0.3, 
    user=Depends(get_current_user)
):
    """Get job recommendations for a student"""
    if user.get("role") == "student" and user["id"] != student_id:
        raise HTTPException(403, "Not authorized")
    
    try:
        student = supabase.table("users").select("skills_embedding").eq("id", student_id).execute()
        if not student.data or not student.data[0].get("skills_embedding"):
            return []
        
        student_vec = student.data[0]["skills_embedding"]
        jobs = supabase.table("jobs").select("*").eq("status", "active").execute()
        
        recommendations = []
        for job in jobs.data:
            if job.get("job_embedding"):
                score = cosine_similarity(student_vec, job["job_embedding"])
                if score >= threshold:
                    company = supabase.table("companies").select("name").eq("id", job["company_id"]).execute()
                    job["company_name"] = company.data[0]["name"] if company.data else "Unknown"
                    recommendations.append({
                        "job": job,
                        "match_score": round(score * 100, 2)
                    })
        
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return recommendations[:20]
    except Exception as e:
        print(f"Error in get_recommendations: {e}")
        return []

# Also handle trailing slash
@router.get("/recommendations/{student_id}/")
async def get_recommendations_trailing(
    student_id: str, 
    threshold: float = 0.3, 
    user=Depends(get_current_user)
):
    return await get_recommendations(student_id, threshold, user)