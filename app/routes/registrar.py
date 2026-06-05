from fastapi import APIRouter
from app.database import supabase

router = APIRouter()

@router.get("/lookup")
async def lookup_student(student_id: str):
    result = supabase.table("registrar_mock").select("student_id").eq("student_id", student_id).maybe_single().execute()
    return {"found": result.data is not None}