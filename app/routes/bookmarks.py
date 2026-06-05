from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def get_bookmarks(user=Depends(get_current_user)):
    if user.get("role") != "student":
        return []
    
    result = supabase.table("bookmarks").select("*, jobs(*)").eq("student_id", user["id"]).execute()
    
    for bookmark in result.data:
        if bookmark.get("jobs") and bookmark["jobs"].get("company_id"):
            company = supabase.table("companies").select("name").eq("id", bookmark["jobs"]["company_id"]).execute()
            if company.data:
                bookmark["jobs"]["company_name"] = company.data[0]["name"]
    
    return result.data

@router.post("/{job_id}")
async def add_bookmark(job_id: str, user=Depends(get_current_user)):
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can bookmark")
    
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