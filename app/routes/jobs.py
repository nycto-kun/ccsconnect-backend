from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.ai_engine import vectorize_text
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

# ============================================================
# GET all jobs (with filters)
# ============================================================
@router.get("/")
async def get_jobs(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    Get all jobs with optional filters.
    - status: filter by job status (active, closed, pending)
    - company_id: filter by specific company
    - For company users, automatically filters to their jobs
    """
    try:
        query = supabase.table("jobs").select("*")
        
        # Apply filters
        if status:
            query = query.eq("status", status)
        
        if company_id:
            query = query.eq("company_id", company_id)
        
        # If logged in as company, only show their jobs
        if user.get("role") == "company":
            # Find company ID from email
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if company.data:
                query = query.eq("company_id", company.data[0]["id"])
            else:
                # Company exists in users but not in companies table? Return empty
                return []
        
        # Execute query
        result = query.order("created_at", desc=True).execute()
        
        # Enrich with company name and application count
        for job in result.data:
            # Get company name
            company = supabase.table("companies").select("name").eq("id", job["company_id"]).execute()
            job["company_name"] = company.data[0]["name"] if company.data else "Unknown"
            
            # Get application count
            apps = supabase.table("applications").select("id", count="exact").eq("job_id", job["id"]).execute()
            job["applicants_count"] = apps.count
        
        return result.data
    except Exception as e:
        print(f"Error in get_jobs: {e}")
        return []


# ============================================================
# GET single job by ID
# ============================================================
@router.get("/{job_id}")
async def get_job(job_id: str, user=Depends(get_current_user)):
    """
    Get detailed information for a specific job.
    Also increments the view count.
    """
    try:
        result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not result.data:
            raise HTTPException(404, "Job not found")
        
        # Increment view count
        current_views = result.data.get("views", 0)
        supabase.table("jobs").update({"views": current_views + 1}).eq("id", job_id).execute()
        
        # Add company name
        company = supabase.table("companies").select("name").eq("id", result.data["company_id"]).execute()
        result.data["company_name"] = company.data[0]["name"] if company.data else "Unknown"
        
        # Add application count
        apps = supabase.table("applications").select("id", count="exact").eq("job_id", job_id).execute()
        result.data["applicants_count"] = apps.count
        
        return result.data
    except Exception as e:
        print(f"Error in get_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# POST create new job
# ============================================================
@router.post("/")
async def create_job(job: dict, user=Depends(get_current_user)):
    """
    Create a new job posting.
    - Company users: auto-assign to their company
    - Admin users: can specify company_id
    """
    try:
        if user.get("role") not in ["company", "admin"]:
            raise HTTPException(403, "Only companies and admins can post jobs")
        
        # Determine company_id
        company_id = None
        
        if user.get("role") == "company":
            # Find company by email
            company_result = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            
            if company_result.data:
                company_id = company_result.data[0]["id"]
            else:
                # Create company record if it doesn't exist
                company_id = str(uuid.uuid4())
                company_data = {
                    "id": company_id,
                    "name": job.get("company_name") or user.get("company_name") or user.get("full_name"),
                    "verified": True,
                    "contact_email": user["email"],
                    "created_at": datetime.utcnow().isoformat()
                }
                supabase.table("companies").insert(company_data).execute()
        else:
            # Admin can specify company_id
            company_id = job.get("company_id")
            if not company_id:
                raise HTTPException(400, "company_id is required for admin job posts")
        
        # Build job data
        data = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "title": job.get("title"),
            "description": job.get("description"),
            "requirements": job.get("requirements", []),
            "location": job.get("location"),
            "salary_range": job.get("salary_range"),
            "duration": job.get("duration", "3 months"),
            "expires_at": job.get("expires_at"),
            "status": job.get("status", "active"),
            "views": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Validate required fields
        if not data["title"] or not data["description"]:
            raise HTTPException(400, "Title and description are required")
        
        # Insert into database
        result = supabase.table("jobs").insert(data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create job")
        
        # Generate AI embedding in background
        try:
            text = f"{data['title']} {data['description']} {' '.join(data['requirements'])}"
            embedding = vectorize_text(text)
            supabase.table("jobs").update({"job_embedding": embedding}).eq("id", result.data[0]["id"]).execute()
        except Exception as e:
            print(f"⚠️ Embedding generation failed (non-critical): {e}")
        
        return {
            "message": "Job posted successfully",
            "job_id": result.data[0]["id"],
            "job": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# PUT update existing job
# ============================================================
@router.put("/{job_id}")
async def update_job(job_id: str, updates: dict, user=Depends(get_current_user)):
    """
    Update an existing job posting.
    - Company users can only update their own jobs
    - Admin users can update any job
    """
    try:
        # Get the job first
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        # Check permissions
        if user.get("role") == "company":
            # Verify this job belongs to the company
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only update your own jobs")
        
        # Allowed fields to update
        allowed_fields = [
            "title", "description", "requirements", "location", 
            "salary_range", "duration", "expires_at", "status"
        ]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
        
        if not filtered_updates:
            raise HTTPException(400, "No valid fields to update")
        
        filtered_updates["updated_at"] = datetime.utcnow().isoformat()
        
        # Update database
        result = supabase.table("jobs").update(filtered_updates).eq("id", job_id).execute()
        
        # Regenerate embedding if title/description/requirements changed
        if any(k in filtered_updates for k in ["title", "description", "requirements"]):
            try:
                updated_job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
                text = f"{updated_job.data['title']} {updated_job.data['description']} {' '.join(updated_job.data.get('requirements', []))}"
                embedding = vectorize_text(text)
                supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
            except Exception as e:
                print(f"⚠️ Embedding update failed: {e}")
        
        return {"message": "Job updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# DELETE job
# ============================================================
@router.delete("/{job_id}")
async def delete_job(job_id: str, user=Depends(get_current_user)):
    """
    Delete a job posting.
    - Company users can only delete their own jobs
    - Admin users can delete any job
    """
    try:
        # Get the job first
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        # Check permissions
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only delete your own jobs")
        
        # Delete related applications first (cascade)
        supabase.table("applications").delete().eq("job_id", job_id).execute()
        
        # Delete bookmarks for this job
        supabase.table("bookmarks").delete().eq("job_id", job_id).execute()
        
        # Delete the job
        supabase.table("jobs").delete().eq("id", job_id).execute()
        
        return {"message": "Job deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# GET jobs by company (convenience endpoint)
# ============================================================
@router.get("/company/my")
async def get_my_company_jobs(user=Depends(get_current_user)):
    """
    Get all jobs for the company of the logged-in user.
    Convenience endpoint for company dashboard.
    """
    try:
        if user.get("role") != "company":
            raise HTTPException(403, "Only company users can access this endpoint")
        
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if not company.data:
            return []
        
        result = supabase.table("jobs").select("*").eq("company_id", company.data[0]["id"]).order("created_at", desc=True).execute()
        
        # Add application count
        for job in result.data:
            apps = supabase.table("applications").select("id", count="exact").eq("job_id", job["id"]).execute()
            job["applicants_count"] = apps.count
        
        return result.data
    except Exception as e:
        print(f"Error in get_my_company_jobs: {e}")
        return []


# ============================================================
# GET applications for a specific job
# ============================================================
@router.get("/{job_id}/applications")
async def get_job_applications(job_id: str, user=Depends(get_current_user)):
    """
    Get all applications for a specific job.
    - Company users: only see applications for their jobs
    - Admin users: see all
    """
    try:
        # Verify job exists
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        # Check permissions
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only view applications for your own jobs")
        
        # Get applications
        result = supabase.table("applications").select("*").eq("job_id", job_id).execute()
        
        # Enrich with student details
        for app in result.data:
            student = supabase.table("users").select("full_name, email, student_id, phone, department, year, skills").eq("id", app["student_id"]).execute()
            if student.data:
                app["student_name"] = student.data[0].get("full_name", "Unknown")
                app["student_email"] = student.data[0].get("email")
                app["student_id_number"] = student.data[0].get("student_id")
                app["student_phone"] = student.data[0].get("phone")
                app["student_department"] = student.data[0].get("department")
                app["student_year"] = student.data[0].get("year")
                app["student_skills"] = student.data[0].get("skills", [])
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_job_applications: {e}")
        return []