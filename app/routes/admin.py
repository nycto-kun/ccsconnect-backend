from fastapi import APIRouter, Depends
from app.database import supabase
from app.routes.auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats")
async def get_admin_stats(user=Depends(require_admin)):
    total_students = supabase.table("users").select("id", count="exact").eq("role", "student").execute().count
    active_jobs = supabase.table("jobs").select("id", count="exact").eq("status", "active").execute().count
    placed_students = supabase.table("applications").select("id", count="exact").eq("status", "accepted").execute().count
    placement_rate = round((placed_students / total_students) * 100, 1) if total_students else 0
    return {
        "totalStudents": total_students,
        "activeJobs": active_jobs,
        "placementRate": placement_rate,
    }

@router.get("/pending-companies")
async def get_pending_companies(user=Depends(require_admin)):
    result = supabase.table("companies").select("*").eq("verified", False).execute()
    return result.data

@router.post("/approve-company/{company_id}")
async def approve_company(company_id: str, user=Depends(require_admin)):
    supabase.table("companies").update({"verified": True}).eq("id", company_id).execute()
    return {"message": "Company approved"}