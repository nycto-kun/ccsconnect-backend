from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_notices(
    type: Optional[str] = None,
    pinned: Optional[bool] = None
):
    """Get all notices (public) - returns empty list if table doesn't exist"""
    try:
        # First, check if the notices table exists
        query = supabase.table("notices").select("*")
        
        if type:
            query = query.eq("type", type)
        if pinned is not None:
            query = query.eq("pinned", pinned)
            
        result = query.order("pinned", desc=True).order("created_at", desc=True).execute()
        
        # Return data (could be empty list)
        return result.data if result.data else []
        
    except Exception as e:
        print(f"Error fetching notices: {e}")
        # Return empty list instead of crashing
        return []

@router.post("/")
async def create_notice(notice: dict, user=Depends(get_current_user)):
    """Create a new notice (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    # Validate required fields
    if not notice.get("title") or not notice.get("content"):
        raise HTTPException(400, "Title and content are required")
    
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
    
    try:
        result = supabase.table("notices").insert(data).execute()
        return {"message": "Notice created", "notice": result.data[0] if result.data else data}
    except Exception as e:
        print(f"Error creating notice: {e}")
        raise HTTPException(500, f"Failed to create notice: {str(e)}")

@router.put("/{notice_id}")
async def update_notice(notice_id: str, updates: dict, user=Depends(get_current_user)):
    """Update a notice (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    allowed_fields = ["title", "content", "type", "pinned", "start_date", "end_date"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    
    if not filtered:
        raise HTTPException(400, "No valid fields to update")
    
    try:
        result = supabase.table("notices").update(filtered).eq("id", notice_id).execute()
        return {"message": "Notice updated"}
    except Exception as e:
        print(f"Error updating notice: {e}")
        raise HTTPException(500, f"Failed to update notice: {str(e)}")

@router.delete("/{notice_id}")
async def delete_notice(notice_id: str, user=Depends(get_current_user)):
    """Delete a notice (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    try:
        supabase.table("notices").delete().eq("id", notice_id).execute()
        return {"message": "Notice deleted"}
    except Exception as e:
        print(f"Error deleting notice: {e}")
        raise HTTPException(500, f"Failed to delete notice: {str(e)}")