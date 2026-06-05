from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/{student_id}/profile")
async def get_student_profile(student_id: str, user=Depends(get_current_user)):
    if user["id"] != student_id and user.get("role") != "admin":
        raise HTTPException(403, "Not authorized")
    
    result = supabase.table("users").select("*").eq("id", student_id).single().execute()
    return result.data