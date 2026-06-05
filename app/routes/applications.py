from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_applications(student_id: str = None, job_id: str = None, user=Depends(get_current_user)):
    query = supabase.table("applications").select("*")
    
    if student_id:
        query = query.eq("student_id", student_id)
    elif user.get("role") == "student":
        query = query.eq("student_id", user["id"])
    
    if job_id:
        query = query.eq("job_id", job_id)
    
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).single().execute()
        if company.data:
            jobs = supabase.table("jobs").select("id").eq("company_id", company.data["id"]).execute()
            job_ids = [j["id"] for j in jobs.data]
            if job_ids:
                query = query.in_("job_id", job_ids)
            else:
                return []
    
    result = query.execute()
    
    for app in result.data:
        job = supabase.table("jobs").select("*").eq("id", app["job_id"]).single().execute()
        if job.data:
            app["job_title"] = job.data["title"]
            company = supabase.table("companies").select("name").eq("id", job.data["company_id"]).single().execute()
            app["company_name"] = company.data["name"] if company.data else "Unknown"
        
        student = supabase.table("users").select("full_name, student_id").eq("id", app["student_id"]).single().execute()
        if student.data:
            app["student_name"] = student.data["full_name"]
            app["roll_number"] = student.data.get("student_id", "")
    
    return result.data

@router.post("/")
async def apply_to_job(job_id: str, user=Depends(get_current_user)):
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can apply")
    
    existing = supabase.table("applications").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
    if existing.data:
        raise HTTPException(400, "You have already applied to this job")
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "job_id": job_id,
        "status": "pending",
        "applied_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("applications").insert(data).execute()
    return {"message": "Application submitted", "application_id": result.data[0]["id"]}

@router.patch("/{application_id}")
async def update_application_status(application_id: str, status: str, user=Depends(get_current_user)):
    if user.get("role") not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    
    app = supabase.table("applications").select("*, jobs(company_id)").eq("id", application_id).single().execute()
    if not app.data:
        raise HTTPException(404, "Application not found")
    
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).single().execute()
        if not company.data or app.data["jobs"]["company_id"] != company.data["id"]:
            raise HTTPException(403, "Not authorized")
    
    supabase.table("applications").update({"status": status, "updated_at": datetime.utcnow().isoformat()}).eq("id", application_id).execute()
    return {"message": "Status updated"}