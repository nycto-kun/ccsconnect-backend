from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def get_bookmarks(user=Depends(get_current_user)):
    if user.get("role") != "student":
        return []
    
    try:
        result = supabase.table("bookmarks").select("*, jobs(*)").eq("student_id", user["id"]).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching bookmarks: {e}")
        return []

@router.post("/{job_id}")
async def add_bookmark(job_id: str, user=Depends(get_current_user)):
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can bookmark")
    
    # Check if already exists
    existing = supabase.table("bookmarks").select("*").eq("student_id", user["id"]).eq("job_id", job_id).execute()
    if existing.data:
        return {"message": "Already bookmarked"}
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "job_id": job_id,
    }
    supabase.table("bookmarks").insert(data).execute()
    return {"message": "Bookmark added"}

@router.delete("/{job_id}")
async def remove_bookmark(job_id: str, user=Depends(get_current_user)):
    supabase.table("bookmarks").delete().eq("student_id", user["id"]).eq("job_id", job_id).execute()
    return {"message": "Bookmark removed"}