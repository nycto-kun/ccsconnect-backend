from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from routes.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])

@router.get("/")
async def get_bookmarks(user=Depends(get_current_user)):
    """Get all bookmarked jobs for the current student"""
    if user["role"] != "student":
        raise HTTPException(403, "Only students can bookmark jobs")
    
    result = supabase.table("bookmarks").select("*, jobs(*)").eq("student_id", user["id"]).execute()
    return result.data

@router.post("/{job_id}")
async def add_bookmark(job_id: str, user=Depends(get_current_user)):
    """Add a job to bookmarks"""
    if user["role"] != "student":
        raise HTTPException(403, "Only students can bookmark jobs")
    
    # Check if already bookmarked
    existing = supabase.table("bookmarks").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
    if existing.data:
        raise HTTPException(400, "Job already bookmarked")
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "job_id": job_id,
        "created_at": datetime.utcnow().isoformat(),
    }
    supabase.table("bookmarks").insert(data).execute()
    return {"message": "Bookmark added"}

@router.delete("/{job_id}")
async def remove_bookmark(job_id: str, user=Depends(get_current_user)):
    """Remove a job from bookmarks"""
    if user["role"] != "student":
        raise HTTPException(403, "Only students can remove bookmarks")
    
    result = supabase.table("bookmarks").delete().eq("student_id", user["id"]).eq("job_id", job_id).execute()
    if not result.data:
        raise HTTPException(404, "Bookmark not found")
    return {"message": "Bookmark removed"}