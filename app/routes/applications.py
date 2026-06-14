from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

# ============================================================
# GET all applications (with filters) - WITH trailing slash
# ============================================================
@router.get("/")
async def get_applications(
    student_id: Optional[str] = None,
    job_id: Optional[str] = None,
    company_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user)
):
    try:
        query = supabase.table("applications").select("*")
        
        # Apply filters
        if student_id:
            query = query.eq("student_id", student_id)
        if job_id:
            query = query.eq("job_id", job_id)
        if status:
            query = query.eq("status", status)
        
        # If student, only their own
        if user.get("role") == "student" and not student_id:
            query = query.eq("student_id", user["id"])
        
        # If company, filter by their jobs
        if user.get("role") == "company":
            # Get company_id from user
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if user_data.data and user_data.data[0].get("company_id"):
                comp_id = user_data.data[0]["company_id"]
                # Get all job ids for this company
                jobs = supabase.table("jobs").select("id").eq("company_id", comp_id).execute()
                job_ids = [j["id"] for j in jobs.data]
                if job_ids:
                    query = query.in_("job_id", job_ids)
                else:
                    return []
            else:
                return []
        
        # If company_id param provided (admin use)
        if company_id:
            jobs = supabase.table("jobs").select("id").eq("company_id", company_id).execute()
            job_ids = [j["id"] for j in jobs.data]
            if job_ids:
                query = query.in_("job_id", job_ids)
            else:
                return []
        
        result = query.order("applied_at", desc=True).execute()
        applications = result.data if result.data else []
        
        # Enrich with job and student details
        for app in applications:
            job = supabase.table("jobs").select("*").eq("id", app["job_id"]).execute()
            if job.data:
                app["job_title"] = job.data[0].get("title", "Unknown")
                company = supabase.table("companies").select("name").eq("id", job.data[0]["company_id"]).execute()
                app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
            
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
# GET all applications - WITHOUT trailing slash (for compatibility)
# ============================================================
@router.get("")
async def get_applications_no_slash(
    student_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user=Depends(get_current_user)
):
    """Handle /applications without trailing slash"""
    return await get_applications(student_id, job_id, company_id, status, user)


# ============================================================
# GET single application by ID - WITH trailing slash
# ============================================================
@router.get("/{application_id}")
async def get_application(application_id: str, user=Depends(get_current_user)):
    """
    Get detailed information for a specific application.
    """
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_application: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# GET single application by ID - WITHOUT trailing slash
# ============================================================
@router.get("/{application_id}")
async def get_application_no_slash(application_id: str, user=Depends(get_current_user)):
    """Handle /applications/{id} without trailing slash"""
    return await get_application(application_id, user)


# ============================================================
# POST apply to a job - WITH trailing slash
# ============================================================
@router.post("/")
async def apply_to_job(job_id: str, user=Depends(get_current_user)):
    try:
        if user.get("role") != "student":
            raise HTTPException(403, "Only students can apply")
        
        # Check if job exists
        job = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        # Check if already applied
        existing = supabase.table("applications").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
        if existing.data:
            raise HTTPException(400, "Already applied")
        
        data = {
            "id": str(uuid.uuid4()),
            "student_id": user["id"],
            "job_id": job_id,
            "status": "pending",
            "applied_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("applications").insert(data).execute()
        return {"message": "Application submitted", "application_id": result.data[0]["id"]}
    except Exception as e:
        print(f"Error applying to job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# POST apply to a job - WITHOUT trailing slash
# ============================================================
@router.post("")
async def apply_to_job_no_slash(job_id: str, user=Depends(get_current_user)):
    """Handle /applications without trailing slash"""
    return await apply_to_job(job_id, user)


# ============================================================
# PATCH update application status - WITH trailing slash
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
    try:
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
        supabase.table("applications").update(update_data).eq("id", application_id).execute()
        
        return {
            "message": f"Application status updated to {status}",
            "application_id": application_id,
            "status": status
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_application_status: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# PATCH update application status - WITHOUT trailing slash
# ============================================================
@router.patch("/{application_id}")
async def update_application_status_no_slash(
    application_id: str,
    status: str,
    notes: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Handle /applications/{id} without trailing slash"""
    return await update_application_status(application_id, status, notes, user)


# ============================================================
# DELETE withdraw application - WITH trailing slash
# ============================================================
@router.delete("/{application_id}")
async def withdraw_application(application_id: str, user=Depends(get_current_user)):
    """
    Withdraw an application.
    Students can withdraw their own pending applications.
    """
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in withdraw_application: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# GET my applications (student convenience) - WITH trailing slash
# ============================================================
@router.get("/my/applications")
async def get_my_applications(user=Depends(get_current_user)):
    """
    Get all applications for the logged-in student.
    Convenience endpoint for student dashboard.
    """
    try:
        if user.get("role") != "student":
            raise HTTPException(403, "Only students can access this endpoint")
        
        result = supabase.table("applications").select("*").eq("student_id", user["id"]).order("applied_at", desc=True).execute()
        applications = result.data if result.data else []
        
        # Enrich with job details
        for app in applications:
            job = supabase.table("jobs").select("title, company_id, location, salary_range, duration").eq("id", app["job_id"]).single().execute()
            if job.data:
                app["job_title"] = job.data.get("title")
                app["job_location"] = job.data.get("location")
                app["job_salary"] = job.data.get("salary_range")
                app["job_duration"] = job.data.get("duration")
                
                company = supabase.table("companies").select("name").eq("id", job.data["company_id"]).execute()
                app["company_name"] = company.data[0]["name"] if company.data else "Unknown"
        
        return applications
    except Exception as e:
        print(f"Error in get_my_applications: {e}")
        return []


# ============================================================
# GET my applications - WITHOUT trailing slash
# ============================================================
@router.get("/my/applications")
async def get_my_applications_no_slash(user=Depends(get_current_user)):
    """Handle /applications/my/applications without trailing slash"""
    return await get_my_applications(user)


# ============================================================
# GET application statistics for a job - WITH trailing slash
# ============================================================
@router.get("/stats/{job_id}")
async def get_application_stats(job_id: str, user=Depends(get_current_user)):
    """
    Get statistics for applications to a specific job.
    Useful for company dashboard charts.
    """
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_application_stats: {e}")
        raise HTTPException(500, str(e))
    
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
    """
    # Allowed statuses
    allowed_statuses = ["pending", "reviewed", "shortlisted", "interview", "accepted", "rejected", "withdrawn"]
    if status not in allowed_statuses:
        raise HTTPException(400, f"Invalid status. Allowed: {', '.join(allowed_statuses)}")
    
    try:
        # Get the application with job details
        app = supabase.table("applications").select("*, jobs(company_id, title)").eq("id", application_id).execute()
        if not app.data:
            raise HTTPException(404, "Application not found")
        
        app_data = app.data[0]
        
        # Check permissions
        if user.get("role") == "company":
            # Get user's company_id
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if not user_data.data or not user_data.data[0].get("company_id"):
                raise HTTPException(403, "No company associated with your account")
            
            company_id = user_data.data[0]["company_id"]
            
            # Verify this job belongs to the company
            if app_data["jobs"]["company_id"] != company_id:
                raise HTTPException(403, "You can only update applications for your own jobs")
                
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
        
        return {
            "message": f"Application status updated to {status}",
            "application_id": application_id,
            "status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating application status: {e}")
        raise HTTPException(500, str(e))

# Also handle trailing slash version
@router.patch("/{application_id}/")
async def update_application_status_trailing(
    application_id: str,
    status: str,
    notes: Optional[str] = None,
    user=Depends(get_current_user)
):
    return await update_application_status(application_id, status, notes, user)

@router.get("/company/interns")
async def get_company_interns(user=Depends(get_current_user)):
    """Get all interns (students) assigned to the logged-in company"""
    if user.get("role") != "company":
        raise HTTPException(403, "Only company users can access this endpoint")
    
    try:
        # Get company_id from user profile
        user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
        if not user_data.data or not user_data.data[0].get("company_id"):
            return []
        
        company_id = user_data.data[0]["company_id"]
        
        # Get all students assigned to this company
        result = supabase.table("users").select("*").eq("company_id", company_id).eq("role", "student").execute()
        
        # Enrich with assignment details
        for student in result.data:
            assignment = supabase.table("assignments").select("*").eq("student_id", student["id"]).eq("company_id", company_id).execute()
            if assignment.data:
                student["assignment"] = assignment.data[0]
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching company interns: {e}")
        return []