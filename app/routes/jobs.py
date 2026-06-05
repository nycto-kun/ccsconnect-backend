from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text
from app.routes.auth import get_current_user, require_admin
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/")
async def get_jobs(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = supabase.table("jobs").select("*")
    if status:
        query = query.eq("status", status)
    if company_id:
        query = query.eq("company_id", company_id)
    
    result = query.execute()
    
    # Enrich with company name
    for job in result.data:
        company = supabase.table("companies").select("name").eq("id", job["company_id"]).single().execute()
        job["company_name"] = company.data["name"] if company.data else None
        
        # Get application count
        apps = supabase.table("applications").select("id", count="exact").eq("job_id", job["id"]).execute()
        job["applicants_count"] = apps.count
    
    return result.data

@router.get("/{job_id}")
async def get_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Job not found")
    
    # Increment view count
    supabase.table("jobs").update({"views": supabase.table("jobs").select("views").eq("id", job_id).execute().data[0].get("views", 0) + 1}).eq("id", job_id).execute()
    
    # Enrich with company name
    company = supabase.table("companies").select("name").eq("id", result.data["company_id"]).single().execute()
    result.data["company_name"] = company.data["name"] if company.data else None
    
    return result.data

@router.post("/")
async def create_job(job: dict, user=Depends(get_current_user)):
    if user["role"] not in ["company", "admin"]:
        raise HTTPException(403, "Only companies or admins can post jobs")
    
    company_id = user["id"] if user["role"] == "company" else job.get("company_id")
    
    data = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "title": job["title"],
        "description": job["description"],
        "requirements": job.get("requirements", []),
        "location": job.get("location"),
        "salary_range": job.get("salary_range"),
        "duration": job.get("duration"),
        "expires_at": job.get("expires_at"),
        "status": "pending",
        "views": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    result = supabase.table("jobs").insert(data).execute()
    
    # Generate embedding in background (or sync)
    text = job["title"] + " " + job["description"] + " " + " ".join(job.get("requirements", []))
    embedding = vectorize_text(text)
    supabase.table("jobs").update({"job_embedding": embedding}).eq("id", result.data[0]["id"]).execute()
    
    return {"message": "Job created", "job_id": result.data[0]["id"]}

@router.patch("/{job_id}")
async def update_job(job_id: str, updates: dict, user=Depends(get_current_user)):
    job = supabase.table("jobs").select("company_id").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    if user["role"] == "company" and job.data["company_id"] != user["id"]:
        raise HTTPException(403, "Not your job")
    
    allowed_fields = ["title", "description", "requirements", "location", "salary_range", "duration", "expires_at", "status"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    
    supabase.table("jobs").update(filtered).eq("id", job_id).execute()
    return {"message": "Job updated"}

@router.delete("/{job_id}")
async def delete_job(job_id: str, user=Depends(get_current_user)):
    job = supabase.table("jobs").select("company_id").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    if user["role"] == "company" and job.data["company_id"] != user["id"]:
        raise HTTPException(403, "Not your job")
    
    supabase.table("jobs").delete().eq("id", job_id).execute()
    return {"message": "Job deleted"}