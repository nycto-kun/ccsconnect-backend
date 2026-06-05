from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

# ============================================================
# GET all applications (with filters)
# ============================================================
@router.get("/")
async def get_applications(
    student_id: Optional[str] = None,
    job_id: Optional[str] = None,
    company_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    Get applications with various filters.
    - student_id: get applications by student
    - job_id: get applications for a specific job
    - company_id: get all applications for a company's jobs
    - status: filter by application status
    """
    query = supabase.table("applications").select("*")
    
    # Apply filters
    if student_id:
        query = query.eq("student_id", student_id)
    
    if job_id:
        query = query.eq("job_id", job_id)
    
    if status:
        query = query.eq("status", status)
    
    # Company filter - get all jobs for the company first
    if company_id:
        jobs = supabase.table("jobs").select("id").eq("company_id", company_id).execute()
        job_ids = [j["id"] for j in jobs.data]
        if job_ids:
            query = query.in_("job_id", job_ids)
        else:
            return []
    
    # If company user, filter to their jobs only
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if company.data:
            jobs = supabase.table("jobs").select("id").eq("company_id", company.data[0]["id"]).execute()
            job_ids = [j["id"] for j in jobs.data]
            if job_ids:
                query = query.in_("job_id", job_ids)
            else:
                return []
    
    # If student user, only show their own applications
    if user.get("role") == "student" and not student_id:
        query = query.eq("student_id", user["id"])
    
    # Execute query
    result = query.order("applied_at", desc=True).execute()
    
    # Enrich with job details
    for app in result.data:
        # Get job details
        job = supabase.table("jobs").select("*").eq("id", app["job_id"]).single().execute()
        if job.data:
            app["job_title"] = job.data.get("title", "Unknown Position")
            app["job_description"] = job.data.get("description")
            app["job_location"] = job.data.get("location")
            app["job_salary"] = job.data.get("salary_range")
            app["job_duration"] = job.data.get("duration")
            
            # Get company name
            company = supabase.table("companies").select("name").eq("id", job.data["company_id"]).execute()
            app["company_name"] = company.data[0]["name"] if company.data else "Unknown Company"
            app["company_id"] = job.data["company_id"]
        
        # Get student details
        student = supabase.table("users").select("full_name, email, student_id, phone, department, year, skills, resume_url").eq("id", app["student_id"]).execute()
        if student.data:
            app["student_name"] = student.data[0].get("full_name", "Unknown Student")
            app["student_email"] = student.data[0].get("email")
            app["student_id_number"] = student.data[0].get("student_id")
            app["student_phone"] = student.data[0].get("phone")
            app["student_department"] = student.data[0].get("department")
            app["student_year"] = student.data[0].get("year")
            app["student_skills"] = student.data[0].get("skills", [])
            app["resume_url"] = student.data[0].get("resume_url")
    
    return result.data


# ============================================================
# GET single application by ID
# ============================================================
@router.get("/{application_id}")
async def get_application(application_id: str, user=Depends(get_current_user)):
    """
    Get detailed information for a specific application.
    """
    result = supabase.table("applications").select("*").eq("id", application_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Application not found")
    
    app = result.data
    
    # Check permissions
    if user.get("role") == "student" and app["student_id"] != user["id"]:
        raise HTTPException(403, "You can only view your own applications")
    
    if user.get("role") == "company":
        job = supabase.table("jobs").select("company_id").eq("id", app["job_id"]).single().execute()
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if not company.data or job.data["company_id"] != company.data[0]["id"]:
            raise HTTPException(403, "You can only view applications for your jobs")
    
    # Enrich with job details
    job = supabase.table("jobs").select("*").eq("id", app["job_id"]).single().execute()
    if job.data:
        app["job_title"] = job.data.get("title")
        app["job_description"] = job.data.get("description")
        
        company = supabase.table("companies").select("name").eq("id", job.data["company_id"]).execute()
        app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
    
    # Enrich with student details
    student = supabase.table("users").select("full_name, email, student_id, phone, department, year, skills, bio, resume_url").eq("id", app["student_id"]).execute()
    if student.data:
        app["student_name"] = student.data[0].get("full_name")
        app["student_email"] = student.data[0].get("email")
        app["student_id_number"] = student.data[0].get("student_id")
        app["student_phone"] = student.data[0].get("phone")
        app["student_department"] = student.data[0].get("department")
        app["student_year"] = student.data[0].get("year")
        app["student_skills"] = student.data[0].get("skills", [])
        app["student_bio"] = student.data[0].get("bio")
        app["resume_url"] = student.data[0].get("resume_url")
    
    return app


# ============================================================
# POST apply to a job
# ============================================================
@router.post("/")
async def apply_to_job(job_id: str, user=Depends(get_current_user)):
    """
    Submit an application for a job.
    Only students can apply.
    """
    # Check role
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can apply for jobs")
    
    # Check if job exists and is active
    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    if job.data.get("status") != "active":
        raise HTTPException(400, "This job is no longer accepting applications")
    
    # Check if already applied
    existing = supabase.table("applications").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
    if existing.data:
        raise HTTPException(400, "You have already applied to this job")
    
    # Create application
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "job_id": job_id,
        "status": "pending",
        "applied_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("applications").insert(data).execute()
    
    if not result.data:
        raise HTTPException(500, "Failed to submit application")
    
    # Optional: Send notification email to company
    # This can be implemented later
    
    return {
        "message": "Application submitted successfully",
        "application_id": result.data[0]["id"],
        "status": "pending"
    }


# ============================================================
# PATCH update application status
# ============================================================
@router.patch("/{application_id}")
async def update_application_status(
    application_id: str,
    status: str,
    notes: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    Update the status of an application.
    - Company users can update applications for their jobs
    - Admin users can update any application
    - Students cannot update status
    """
    # Allowed statuses
    allowed_statuses = ["pending", "reviewed", "shortlisted", "interview", "accepted", "rejected", "withdrawn"]
    if status not in allowed_statuses:
        raise HTTPException(400, f"Invalid status. Allowed: {', '.join(allowed_statuses)}")
    
    # Get the application
    app = supabase.table("applications").select("*, jobs(company_id)").eq("id", application_id).single().execute()
    if not app.data:
        raise HTTPException(404, "Application not found")
    
    # Check permissions
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if not company.data or app.data["jobs"]["company_id"] != company.data[0]["id"]:
            raise HTTPException(403, "You can only update applications for your jobs")
    elif user.get("role") == "student":
        raise HTTPException(403, "Students cannot update application status")
    # Admin can update any
    
    # Prepare update data
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if notes:
        update_data["notes"] = notes
    
    # Update database
    result = supabase.table("applications").update(update_data).eq("id", application_id).execute()
    
    # Optional: Send notification email to student
    # This can be implemented later
    
    return {
        "message": f"Application status updated to {status}",
        "application_id": application_id,
        "status": status
    }


# ============================================================
# DELETE withdraw application
# ============================================================
@router.delete("/{application_id}")
async def withdraw_application(application_id: str, user=Depends(get_current_user)):
    """
    Withdraw an application.
    Students can withdraw their own pending applications.
    """
    # Get the application
    app = supabase.table("applications").select("*").eq("id", application_id).single().execute()
    if not app.data:
        raise HTTPException(404, "Application not found")
    
    # Check permissions
    if user.get("role") == "student":
        if app.data["student_id"] != user["id"]:
            raise HTTPException(403, "You can only withdraw your own applications")
        
        # Only allow withdrawal if status is pending
        if app.data["status"] not in ["pending", "reviewed"]:
            raise HTTPException(400, f"Cannot withdraw application with status: {app.data['status']}")
        
        # Update status to withdrawn
        supabase.table("applications").update({
            "status": "withdrawn",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", application_id).execute()
        
        return {"message": "Application withdrawn successfully"}
    
    # Admin or company can delete applications
    if user.get("role") in ["admin", "company"]:
        supabase.table("applications").delete().eq("id", application_id).execute()
        return {"message": "Application deleted successfully"}
    
    raise HTTPException(403, "Not authorized to perform this action")


# ============================================================
# GET applications for current student (convenience)
# ============================================================
@router.get("/my/applications")
async def get_my_applications(user=Depends(get_current_user)):
    """
    Get all applications for the logged-in student.
    Convenience endpoint for student dashboard.
    """
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can access this endpoint")
    
    result = supabase.table("applications").select("*").eq("student_id", user["id"]).order("applied_at", desc=True).execute()
    
    # Enrich with job details
    for app in result.data:
        job = supabase.table("jobs").select("title, company_id, location, salary_range, duration").eq("id", app["job_id"]).single().execute()
        if job.data:
            app["job_title"] = job.data.get("title")
            app["job_location"] = job.data.get("location")
            app["job_salary"] = job.data.get("salary_range")
            app["job_duration"] = job.data.get("duration")
            
            company = supabase.table("companies").select("name").eq("id", job.data["company_id"]).execute()
            app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
    
    return result.data


# ============================================================
# GET application statistics for a job
# ============================================================
@router.get("/stats/{job_id}")
async def get_application_stats(job_id: str, user=Depends(get_current_user)):
    """
    Get statistics for applications to a specific job.
    Useful for company dashboard charts.
    """
    # Verify job exists and user has permission
    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(404, "Job not found")
    
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if not company.data or job.data["company_id"] != company.data[0]["id"]:
            raise HTTPException(403, "You can only view stats for your own jobs")
    
    # Get all applications
    apps = supabase.table("applications").select("*").eq("job_id", job_id).execute()
    
    # Calculate statistics
    stats = {
        "total": len(apps.data),
        "pending": len([a for a in apps.data if a["status"] == "pending"]),
        "reviewed": len([a for a in apps.data if a["status"] == "reviewed"]),
        "shortlisted": len([a for a in apps.data if a["status"] == "shortlisted"]),
        "interview": len([a for a in apps.data if a["status"] == "interview"]),
        "accepted": len([a for a in apps.data if a["status"] == "accepted"]),
        "rejected": len([a for a in apps.data if a["status"] == "rejected"]),
        "withdrawn": len([a for a in apps.data if a["status"] == "withdrawn"])
    }
    
    return stats