from fastapi import APIRouter, Depends
from app.database import supabase
from app.routes.auth import require_admin
from datetime import datetime

router = APIRouter()

@router.get("/stats")
async def get_admin_stats(user=Depends(require_admin)):
    students = supabase.table("users").select("id", count="exact").eq("role", "student").execute()
    active_jobs = supabase.table("jobs").select("id", count="exact").eq("status", "active").execute()
    placed = supabase.table("applications").select("id", count="exact").eq("status", "accepted").execute()
    pending_companies = supabase.table("companies").select("id", count="exact").eq("verified", False).execute()
    
    placement_rate = round((placed.count / students.count) * 100, 1) if students.count > 0 else 0
    
    return {
        "totalStudents": students.count,
        "activeJobs": active_jobs.count,
        "placementRate": placement_rate,
        "pendingApprovals": pending_companies.count,
        "totalPlacements": placed.count,
        "lastUpdated": datetime.utcnow().isoformat()
    }

@router.get("/pending-companies")
async def get_pending_companies(user=Depends(require_admin)):
    result = supabase.table("companies").select("*").eq("verified", False).execute()
    return result.data

@router.post("/approve-company/{company_id}")
async def approve_company(company_id: str, user=Depends(require_admin)):
    supabase.table("companies").update({"verified": True}).eq("id", company_id).execute()
    return {"message": "Company approved"}

@router.delete("/reject-company/{company_id}")
async def reject_company(company_id: str, user=Depends(require_admin)):
    supabase.table("companies").delete().eq("id", company_id).execute()
    return {"message": "Company rejected"}

@router.get("/users")
async def get_all_users(role: str = None, user=Depends(require_admin)):
    """Get all users (admin only) - for student management tab"""
    query = supabase.table("users").select("*")
    if role:
        query = query.eq("role", role)
    result = query.execute()
    return result.data