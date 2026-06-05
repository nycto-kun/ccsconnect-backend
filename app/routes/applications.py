from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from routes.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.get("/")
async def get_applications(
    student_id: str = None,
    job_id: str = None,
    user=Depends(get_current_user)
):
    query = supabase.table("applications").select("*")
    if student_id:
        query = query.eq("student_id", student_id)
    if job_id:
        query = query.eq("job_id", job_id)
    # If company user, filter jobs where company_id matches (requires join)
    if user["role"] == "company":
        # Get all job ids for this company
        jobs = supabase.table("jobs").select("id").eq("company_id", user["id"]).execute()
        job_ids = [j["id"] for j in jobs.data]
        if job_ids:
            query = query.in_("job_id", job_ids)
        else:
            return []
    result = query.execute()
    # Enrich with job details
    for app in result.data:
        job = supabase.table("jobs").select("*").eq("id", app["job_id"]).single().execute()
        app["job_title"] = job.data["title"] if job.data else None
        app["company_name"] = job.data["company_name"] if job.data else None
    return result.data

@router.post("/")
async def apply_to_job(job_id: str, user=Depends(get_current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Only students can apply")
    # Check existing
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
    # Only company or admin can update status
    if user["role"] not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    # Verify company owns the job (if company)
    app = supabase.table("applications").select("*, jobs(company_id)").eq("id", application_id).single().execute()
    if not app.data:
        raise HTTPException(404, "Application not found")
    if user["role"] == "company" and app.data["jobs"]["company_id"] != user["id"]:
        raise HTTPException(403, "Not your job")
    supabase.table("applications").update({"status": status, "updated_at": datetime.utcnow().isoformat()}).eq("id", application_id).execute()
    return {"message": "Status updated"}