from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

# NO prefix here - prefix is set in main.py
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
    """
    try:
        query = supabase.table("applications").select("*")
        
        # Apply filters
        if student_id:
            query = query.eq("student_id", student_id)
        
        if job_id:
            query = query.eq("job_id", job_id)
        
        if status:
            query = query.eq("status", status)
        
        # If student, only their own applications
        if user.get("role") == "student" and not student_id:
            query = query.eq("student_id", user["id"])
        
        # If company, filter by their jobs
        if user.get("role") == "company":
            # Get user's company ID
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if company.data:
                # Get all job IDs for this company
                jobs = supabase.table("jobs").select("id").eq("company_id", company.data[0]["id"]).execute()
                job_ids = [j["id"] for j in jobs.data]
                if job_ids:
                    query = query.in_("job_id", job_ids)
                else:
                    return []
        
        # Execute query
        result = query.order("applied_at", desc=True).execute()
        applications = result.data if result.data else []
        
        # Enrich with job and student details
        for app in applications:
            # Get job details
            job = supabase.table("jobs").select("*").eq("id", app["job_id"]).execute()
            if job.data:
                app["job_title"] = job.data[0].get("title", "Unknown")
                app["job_location"] = job.data[0].get("location")
                app["job_salary"] = job.data[0].get("salary_range")
                # Get company name
                company = supabase.table("companies").select("name").eq("id", job.data[0]["company_id"]).execute()
                app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
            
            # Get student details
            student = supabase.table("users").select("full_name, email, student_id").eq("id", app["student_id"]).execute()
            if student.data:
                app["student_name"] = student.data[0].get("full_name", "Unknown")
                app["student_email"] = student.data[0].get("email")
                app["roll_number"] = student.data[0].get("student_id")
        
        return applications
    except Exception as e:
        print(f"Error in get_applications: {e}")
        return []


# ============================================================
# GET single application by ID
# ============================================================
@router.get("/{application_id}")
async def get_application(application_id: str, user=Depends(get_current_user)):
    try:
        result = supabase.table("applications").select("*").eq("id", application_id).execute()
        if not result.data:
            raise HTTPException(404, "Application not found")
        
        app = result.data[0]
        
        # Check permissions
        if user.get("role") == "student" and app["student_id"] != user["id"]:
            raise HTTPException(403, "Not your application")
        
        # Enrich with job details
        job = supabase.table("jobs").select("*").eq("id", app["job_id"]).execute()
        if job.data:
            app["job_title"] = job.data[0].get("title")
            company = supabase.table("companies").select("name").eq("id", job.data[0]["company_id"]).execute()
            app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
        
        return app
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_application: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# POST create new application
# ============================================================
@router.post("/")
async def apply_to_job(job_id: str, user=Depends(get_current_user)):
    try:
        if user.get("role") != "student":
            raise HTTPException(403, "Only students can apply")
        
        # Check if already applied
        existing = supabase.table("applications").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
        if existing.data:
            raise HTTPException(400, "Already applied to this job")
        
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
        
        return {
            "message": "Application submitted successfully",
            "application_id": result.data[0]["id"],
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in apply_to_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# PATCH update application status
# ============================================================
@router.patch("/{application_id}")
async def update_application_status(
    application_id: str,
    status: str,
    user=Depends(get_current_user)
):
    allowed_statuses = ["pending", "reviewed", "shortlisted", "interview", "accepted", "rejected"]
    if status not in allowed_statuses:
        raise HTTPException(400, f"Invalid status. Allowed: {', '.join(allowed_statuses)}")
    
    try:
        # Get application
        app = supabase.table("applications").select("*, jobs(company_id)").eq("id", application_id).execute()
        if not app.data:
            raise HTTPException(404, "Application not found")
        
        app_data = app.data[0]
        
        # Check permissions
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or app_data["jobs"]["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "Not your application")
        elif user.get("role") not in ["admin"]:
            raise HTTPException(403, "Not authorized")
        
        # Update status
        supabase.table("applications").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", application_id).execute()
        
        return {"message": f"Status updated to {status}"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_application_status: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# DELETE withdraw application
# ============================================================
@router.delete("/{application_id}")
async def withdraw_application(application_id: str, user=Depends(get_current_user)):
    try:
        app = supabase.table("applications").select("*").eq("id", application_id).execute()
        if not app.data:
            raise HTTPException(404, "Application not found")
        
        app_data = app.data[0]
        
        if user.get("role") == "student":
            if app_data["student_id"] != user["id"]:
                raise HTTPException(403, "Not your application")
            if app_data["status"] not in ["pending", "reviewed"]:
                raise HTTPException(400, "Cannot withdraw application at this stage")
            
            supabase.table("applications").update({
                "status": "withdrawn",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", application_id).execute()
            
            return {"message": "Application withdrawn"}
        
        # Admin or company can delete
        supabase.table("applications").delete().eq("id", application_id).execute()
        return {"message": "Application deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in withdraw_application: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# GET my applications (student convenience)
# ============================================================
@router.get("/my/applications")
async def get_my_applications(user=Depends(get_current_user)):
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can access this endpoint")
    
    try:
        result = supabase.table("applications").select("*").eq("student_id", user["id"]).order("applied_at", desc=True).execute()
        applications = result.data if result.data else []
        
        for app in applications:
            job = supabase.table("jobs").select("title, company_id").eq("id", app["job_id"]).execute()
            if job.data:
                app["job_title"] = job.data[0].get("title")
                company = supabase.table("companies").select("name").eq("id", job.data[0]["company_id"]).execute()
                app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
        
        return applications
    except Exception as e:
        print(f"Error in get_my_applications: {e}")
        return []