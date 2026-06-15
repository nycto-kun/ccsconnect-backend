from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text, cosine_similarity
from app.routes.auth import get_current_user
from typing import List, Optional
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/recommendations/{student_id}")
async def get_recommendations(
    student_id: str, 
    threshold: float = 0.1, 
    limit: int = 20,
    user=Depends(get_current_user)
):
    """Get job recommendations for a student"""
    try:
        logger.info(f"Recommendations requested for student: {student_id}")
        logger.info(f"Current user: {user.get('id') if user else 'None'}")
        
        # Allow students to get their own recommendations
        if user.get("role") == "student" and user["id"] != student_id:
            logger.warning(f"Student {user['id']} tried to access {student_id}")
            raise HTTPException(403, "Not authorized")
        
        # Get student data
        student = supabase.table("users").select("*").eq("id", student_id).execute()
        if not student.data:
            logger.warning(f"Student {student_id} not found")
            return []
        
        student_data = student.data[0]
        student_skills = student_data.get("skills", [])
        student_embedding = student_data.get("skills_embedding")
        
        logger.info(f"Student skills: {student_skills}")
        
        # Generate embedding if missing
        if not student_embedding and student_skills:
            text = " ".join(student_skills)
            student_embedding = vectorize_text(text)
            supabase.table("users").update({"skills_embedding": student_embedding}).eq("id", student_id).execute()
            logger.info(f"Generated new embedding for student {student_id}")
        
        if not student_embedding:
            logger.warning(f"No embedding for student {student_id}")
            return []
        
        # Get all active jobs
        jobs = supabase.table("jobs").select("*").eq("status", "active").execute()
        logger.info(f"Found {len(jobs.data)} active jobs")
        
        recommendations = []
        for job in jobs.data:
            try:
                job_embedding = job.get("job_embedding")
                
                # Generate embedding for job if missing
                if not job_embedding:
                    text = job["title"] + " " + job.get("description", "") + " " + " ".join(job.get("requirements", []))
                    job_embedding = vectorize_text(text)
                    supabase.table("jobs").update({"job_embedding": job_embedding}).eq("id", job["id"]).execute()
                
                if job_embedding:
                    score = cosine_similarity(student_embedding, job_embedding)
                    if score >= threshold:
                        # Get company name
                        company = supabase.table("companies").select("name").eq("id", job["company_id"]).execute()
                        job["company_name"] = company.data[0]["name"] if company.data else "Unknown"
                        
                        recommendations.append({
                            "job": job,
                            "match_score": round(score * 100, 2)
                        })
            except Exception as e:
                logger.error(f"Error processing job {job.get('id')}: {e}")
                continue
        
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        logger.info(f"Returning {len(recommendations)} recommendations")
        return recommendations[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recommendations: {e}")
        logger.error(traceback.format_exc())
        return []

@router.get("/recommendations/student/me")
async def get_my_recommendations(threshold: float = 0.1, user=Depends(get_current_user)):
    """Get recommendations for the currently logged-in student"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can get recommendations")
    return await get_recommendations(user["id"], threshold)

@router.post("/student-embedding")
async def update_student_embedding(
    request: dict,
    user=Depends(get_current_user)
):
    """Generate and store embedding for a student"""
    try:
        logger.info(f"Student embedding request for user: {user['id']}")
        
        if user.get("role") != "student":
            raise HTTPException(403, "Only students can update their embedding")
        
        skills = request.get("skills", [])
        resume_text = request.get("resume_text", "")
        
        text = " ".join(skills) + " " + resume_text
        embedding = vectorize_text(text) if text.strip() else [0.0] * 384
        
        supabase.table("users").update({
            "skills_embedding": embedding,
            "skills": skills,
            "resume_text": resume_text[:5000] if resume_text else ""
        }).eq("id", user["id"]).execute()
        
        return {"message": "Embedding updated", "skills_count": len(skills)}
    except Exception as e:
        logger.error(f"Error in student-embedding: {e}")
        raise HTTPException(500, str(e))

@router.post("/job-embedding/{job_id}")
async def update_job_embedding(job_id: str, user=Depends(get_current_user)):
    """Generate and store embedding for a job"""
    try:
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        text = job.data["title"] + " " + job.data.get("description", "") + " " + " ".join(job.data.get("requirements", []))
        embedding = vectorize_text(text)
        
        supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
        return {"message": "Job embedding updated"}
    except Exception as e:
        logger.error(f"Error in job-embedding: {e}")
        raise HTTPException(500, str(e))

@router.get("/ping")
async def ping():
    return {"message": "AI router is working"}