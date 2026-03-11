from fastapi import APIRouter, HTTPException
from app.database import supabase
from app.ai_engine import vectorize_text, cosine_similarity
from app.models import JobCreate
from typing import List

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/")
async def create_job(job: JobCreate):
    text = job.title + " " + job.description + " " + " ".join(job.requirements)
    embedding = vectorize_text(text)

    job_data = job.dict()
    job_data["job_embedding"] = embedding
    result = supabase.table("jobs").insert(job_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Job creation failed")
    return {"job_id": result.data[0]["id"]}

@router.get("/recommendations/{student_id}")
async def get_recommendations(student_id: str, threshold: float = 0.6):
    student = supabase.table("student_profiles").select("skills_embedding").eq("user_id", student_id).single().execute()
    if not student.data or not student.data.get("skills_embedding"):
        raise HTTPException(status_code=404, detail="Student profile or embedding not found")
    student_vec = student.data["skills_embedding"]

    jobs = supabase.table("jobs").select("*").eq("status", "approved").execute()
    recommendations = []

    for job in jobs.data:
        if job.get("job_embedding"):
            score = cosine_similarity(student_vec, job["job_embedding"])
            if score >= threshold:
                recommendations.append({
                    "job": job,
                    "match_score": round(score * 100, 2)
                })

    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations

@router.post("/students/{student_id}/embed")
async def update_student_embedding(student_id: str):
    student = supabase.table("student_profiles").select("skills, resume_url").eq("user_id", student_id).single().execute()
    if not student.data:
        raise HTTPException(status_code=404, detail="Student not found")

    skills_text = " ".join(student.data.get("skills", []))
    text_to_embed = skills_text
    embedding = vectorize_text(text_to_embed)

    supabase.table("student_profiles").update({"skills_embedding": embedding}).eq("user_id", student_id).execute()
    return {"message": "Embedding updated"}

@router.get("/")
async def get_jobs(status: str = None):
    query = supabase.table("jobs").select("*")
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data