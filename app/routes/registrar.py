from fastapi import APIRouter, HTTPException
from app.database import supabase

router = APIRouter(prefix="/api/registrar", tags=["Registrar"])

@router.get("/lookup")
async def lookup_student(student_id: str):
    result = supabase.table("registrar_mock").select("*").eq("student_id", student_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Student not found")
    return result.data