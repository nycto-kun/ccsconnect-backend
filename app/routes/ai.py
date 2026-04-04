from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text, cosine_similarity
from app.models import SkillsEmbeddingRequest, JobEmbeddingRequest
from app.routes.auth import get_current_user, require_admin
from typing import List

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/student-embedding")
async def update_student_embedding(req: SkillsEmbeddingRequest, user=Depends(get_current_user)):
    # Combine skills and resume text
    text = " ".join(req.skills) + " " + (req.resume_text or "")
    embedding = vectorize_text(text)
    supabase.table("student_profiles").update({"skills_embedding": embedding}).eq("user_id", user["id"]).execute()
    return {"message": "Student embedding updated"}

@router.post("/job-embedding/{job_id}")
async def update_job_embedding(job_id: str, req: JobEmbeddingRequest, user=Depends(require_admin)):
    text = req.title + " " + req.description + " " + " ".join(req.requirements)
    embedding = vectorize_text(text)
    supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
    return {"message": "Job embedding updated"}

@router.get("/recommendations/{student_id}")
async def get_recommendations(student_id: str, limit: int = 10):
    # Fetch student embedding
    student = supabase.table("student_profiles").select("skills_embedding").eq("user_id", student_id).single().execute()
    if not student.data or not student.data.get("skills_embedding"):
        raise HTTPException(404, "Student embedding not found")
    student_vec = student.data["skills_embedding"]

    # Fetch all jobs with job_embedding
    jobs = supabase.table("jobs").select("*").not_.is_("job_embedding", "null").execute()
    recommendations = []
    for job in jobs.data:
        score = cosine_similarity(student_vec, job["job_embedding"])
        if score >= 0.6:
            recommendations.append({
                "job": job,
                "match_score": round(score * 100, 2)
            })
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:limit]