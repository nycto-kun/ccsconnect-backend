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
    """Get all jobs with optional filters."""
    try:
        query = supabase.table("jobs").select("*")
        
        if status:
            query = query.eq("status", status)
        
        if company_id:
            query = query.eq("company_id", company_id)
        
        # If logged in as company, only show their jobs
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if company.data:
                query = query.eq("company_id", company.data[0]["id"])
            else:
                return []
        
        result = query.order("created_at", desc=True).execute()
        
        # Enrich with company name and application count
        for job in result.data:
            company = supabase.table("companies").select("name").eq("id", job["company_id"]).execute()
            job["company_name"] = company.data[0]["name"] if company.data else "Unknown"
            
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
    """Get detailed information for a specific job."""
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# POST create new job - WITH AUTO-GENERATED EMBEDDING
# ============================================================
@router.post("/")
async def create_job(job: dict, user=Depends(get_current_user)):
    """Create a new job posting with auto-generated AI embedding."""
    try:
        if user.get("role") not in ["company", "admin"]:
            raise HTTPException(403, "Only companies and admins can post jobs")
        
        if not job.get("title") or not job.get("description"):
            raise HTTPException(400, "Title and description are required")
        
        company_id = None
        
        if user.get("role") == "company":
            # First check if user already has a company_id in their profile
            if user.get("company_id"):
                company_id = user["company_id"]
                # Verify it exists in companies table
                company_check = supabase.table("companies").select("id").eq("id", company_id).execute()
                if not company_check.data:
                    company_id = None
            
            # If no company_id, try to find by email
            if not company_id:
                company_result = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
                if company_result.data:
                    company_id = company_result.data[0]["id"]
            
            # If still no company, create one
            if not company_id:
                company_id = str(uuid.uuid4())
                company_data = {
                    "id": company_id,
                    "name": job.get("company_name") or user.get("company_name") or user.get("full_name"),
                    "verified": True,
                    "contact_email": user["email"],
                    "created_at": datetime.utcnow().isoformat()
                }
                supabase.table("companies").insert(company_data).execute()
                
                # Update user with company_id
                supabase.table("users").update({"company_id": company_id}).eq("id", user["id"]).execute()
        else:
            company_id = job.get("company_id")
            if not company_id:
                raise HTTPException(400, "company_id required for admin posts")
            
            # Verify company exists
            company_check = supabase.table("companies").select("id").eq("id", company_id).execute()
            if not company_check.data:
                raise HTTPException(400, f"Company with id {company_id} does not exist")
        
        # Create the job
        data = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "title": job.get("title"),
            "description": job.get("description"),
            "requirements": job.get("requirements", []),
            "location": job.get("location", ""),
            "salary_range": job.get("salary_range", ""),
            "duration": job.get("duration", "3 months"),
            "expires_at": job.get("expires_at"),
            "status": "active",
            "views": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("jobs").insert(data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create job")
        
        # 🔥🔥🔥 AUTO-GENERATE EMBEDDING FOR THE JOB 🔥🔥🔥
        try:
            # Combine title, description, and requirements for embedding
            text = f"{data['title']} {data['description']} {' '.join(data['requirements'])}"
            print(f"Generating embedding for job: {data['title']}")
            print(f"Text length: {len(text)}")
            
            embedding = vectorize_text(text)
            
            # Update the job with the embedding
            supabase.table("jobs").update({"job_embedding": embedding}).eq("id", result.data[0]["id"]).execute()
            print(f"✅ Auto-generated embedding for job: {data['title']}")
        except Exception as e:
            print(f"⚠️ Embedding generation failed (non-critical): {e}")
        
        return {
            "message": "Job posted successfully",
            "job_id": result.data[0]["id"],
            "job": result.data[0],
            "embedding_generated": True
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating job: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# PUT update existing job - WITH EMBEDDING REGENERATION
# ============================================================
@router.put("/{job_id}")
async def update_job(job_id: str, updates: dict, user=Depends(get_current_user)):
    """Update an existing job posting and regenerate embedding."""
    try:
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only update your own jobs")
        
        allowed_fields = ["title", "description", "requirements", "location", "salary_range", "duration", "expires_at", "status"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
        
        if not filtered_updates:
            raise HTTPException(400, "No valid fields to update")
        
        filtered_updates["updated_at"] = datetime.utcnow().isoformat()
        
        supabase.table("jobs").update(filtered_updates).eq("id", job_id).execute()
        
        # 🔥 REGENERATE EMBEDDING AFTER UPDATE 🔥
        try:
            updated_job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
            if updated_job.data:
                text = f"{updated_job.data['title']} {updated_job.data['description']} {' '.join(updated_job.data.get('requirements', []))}"
                embedding = vectorize_text(text)
                supabase.table("jobs").update({"job_embedding": embedding}).eq("id", job_id).execute()
                print(f"✅ Regenerated embedding for job: {updated_job.data['title']}")
        except Exception as e:
            print(f"⚠️ Embedding regeneration failed: {e}")
        
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
    """Delete a job posting."""
    try:
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only delete your own jobs")
        
        # Delete related applications and bookmarks
        supabase.table("applications").delete().eq("job_id", job_id).execute()
        supabase.table("bookmarks").delete().eq("job_id", job_id).execute()
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
    """Get all jobs for the logged-in company."""
    try:
        if user.get("role") != "company":
            raise HTTPException(403, "Only company users can access this endpoint")
        
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
        if not company.data:
            return []
        
        result = supabase.table("jobs").select("*").eq("company_id", company.data[0]["id"]).order("created_at", desc=True).execute()
        
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
    """Get all applications for a specific job."""
    try:
        job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job.data:
            raise HTTPException(404, "Job not found")
        
        if user.get("role") == "company":
            company = supabase.table("companies").select("id").eq("contact_email", user["email"]).execute()
            if not company.data or job.data["company_id"] != company.data[0]["id"]:
                raise HTTPException(403, "You can only view applications for your own jobs")
        
        result = supabase.table("applications").select("*").eq("job_id", job_id).execute()
        
        for app in result.data:
            student = supabase.table("users").select("full_name, email, student_id").eq("id", app["student_id"]).execute()
            if student.data:
                app["student_name"] = student.data[0].get("full_name", "Unknown")
                app["student_email"] = student.data[0].get("email")
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_job_applications: {e}")
        return []