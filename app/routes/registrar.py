from fastapi import APIRouter, HTTPException
from app.database import supabase

router = APIRouter(prefix="/api/registrar", tags=["Registrar"])

@router.get("/lookup")
async def lookup_student(student_id: str):
    """
    Check if a student exists. Returns only existence status for privacy.
    """
    result = supabase.table("registrar_mock").select("student_id").eq("student_id", student_id).maybe_single().execute()
    return {"found": result.data is not None}