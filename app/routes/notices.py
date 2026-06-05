from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_notices(type: str = None, pinned: bool = None):
    query = supabase.table("notices").select("*")
    if type:
        query = query.eq("type", type)
    if pinned is not None:
        query = query.eq("pinned", pinned)
    result = query.order("pinned", desc=True).order("created_at", desc=True).execute()
    return result.data

@router.post("/")
async def create_notice(notice: dict, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    data = {
        "id": str(uuid.uuid4()),
        "title": notice.get("title"),
        "content": notice.get("content"),
        "type": notice.get("type", "internship"),
        "pinned": notice.get("pinned", False),
        "start_date": notice.get("start_date"),
        "end_date": notice.get("end_date"),
        "created_by": user["id"],
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("notices").insert(data).execute()
    return {"message": "Notice created", "notice": result.data[0]}

@router.put("/{notice_id}")
async def update_notice(notice_id: str, updates: dict, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    allowed_fields = ["title", "content", "type", "pinned", "start_date", "end_date"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    supabase.table("notices").update(filtered).eq("id", notice_id).execute()
    return {"message": "Notice updated"}

@router.delete("/{notice_id}")
async def delete_notice(notice_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    supabase.table("notices").delete().eq("id", notice_id).execute()
    return {"message": "Notice deleted"}