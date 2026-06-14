from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text, cosine_similarity
from app.routes.auth import get_current_user
import numpy as np

router = APIRouter()

@router.post("/student-embedding")
async def update_student_embedding(
    skills: list[str], 
    resume_text: str = "", 
    user=Depends(get_current_user)
):
    """Generate and store embedding for a student based on skills + resume"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can update their embedding")
    
    # Combine skills and resume text
    text = " ".join(skills) + " " + resume_text
    if not text.strip():
        # Return zero vector if no data
        embedding = [0.0] * 384
    else:
        embedding = vectorize_text(text)
    
    # Update user profile
    supabase.table("users").update({
        "skills_embedding": embedding,
        "skills": skills,
        "resume_text": resume_text[:5000] if resume_text else "",
        "updated_at": "now()"
    }).eq("id", user["id"]).execute()
    
    return {"message": "Embedding updated", "skills_count": len(skills)}

@router.post("/job-embedding/{job_id}")
async def update_job_embedding(job_id: str, user=Depends(get_current_user)):
    """Generate and store embedding for a job posting"""
    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    # Combine job data
    text = job.data["title"] + " " + job.data["description"] + " " + " ".join(job.data.get("requirements", []))
    embedding = vectorize_text(text)
    
    supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
    return {"message": "Job embedding updated"}

@router.get("/recommendations/{student_id}")
async def get_recommendations(
    student_id: str, 
    threshold: float = 0.3, 
    limit: int = 20,
    user=Depends(get_current_user)
):
    """Get job recommendations for a student based on embedding similarity"""
    # Check permissions
    if user.get("role") == "student" and user["id"] != student_id:
        raise HTTPException(403, "Not authorized")
    
    # Get student embedding
    student = supabase.table("users").select("skills_embedding, skills, full_name").eq("id", student_id).execute()
    if not student.data:
        return []
    
    student_data = student.data[0]
    student_vec = student_data.get("skills_embedding")
    
    # If no embedding, return empty
    if not student_vec:
        return []
    
    # Get all active jobs
    jobs = supabase.table("jobs").select("*").eq("status", "active").execute()
    
    recommendations = []
    for job in jobs.data:
        job_vec = job.get("job_embedding")
        if job_vec:
            try:
                score = cosine_similarity(student_vec, job_vec)
                if score >= threshold:
                    # Get company name
                    company = supabase.table("companies").select("name").eq("id", job["company_id"]).execute()
                    job["company_name"] = company.data[0]["name"] if company.data else "Unknown Company"
                    
                    # Add additional job data
                    job["applicants_count"] = supabase.table("applications").select("id", count="exact").eq("job_id", job["id"]).execute().count
                    
                    recommendations.append({
                        "job": job,
                        "match_score": round(score * 100, 2)
                    })
            except Exception as e:
                print(f"Error calculating similarity for job {job['id']}: {e}")
                continue
    
    # Sort by match score (highest first)
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return limited results
    return recommendations[:limit]

@router.get("/recommendations/student/me")
async def get_my_recommendations(threshold: float = 0.3, user=Depends(get_current_user)):
    """Get recommendations for the currently logged-in student"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can get recommendations")
    return await get_recommendations(user["id"], threshold)