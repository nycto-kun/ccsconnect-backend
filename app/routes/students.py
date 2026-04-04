from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/{student_id}/profile")
async def get_student_profile(student_id: str, user=Depends(get_current_user)):
    # Only allow the student themselves or admin to view
    if user["id"] != student_id and user["role"] != "admin":
        raise HTTPException(403, "Not authorized")
    result = supabase.table("student_profiles").select("*").eq("user_id", student_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Student profile not found")
    return result.data