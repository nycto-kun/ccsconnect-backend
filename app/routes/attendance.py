from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from routes.auth import get_current_user
import uuid
from datetime import date

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("/")
async def log_attendance(
    student_id: str,
    date_str: str,
    hours_worked: float,
    status: str,
    task: str,
    user=Depends(get_current_user)
):
    if user["role"] not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    data = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "company_id": user["id"] if user["role"] == "company" else None,
        "date": date_str,
        "hours_worked": hours_worked,
        "status": status,
        "task": task,
        "logged_by": user["full_name"],
    }
    supabase.table("attendance").insert(data).execute()
    return {"message": "Attendance logged"}

@router.get("/")
async def get_attendance(student_id: str = None, user=Depends(get_current_user)):
    query = supabase.table("attendance").select("*")
    if student_id:
        query = query.eq("student_id", student_id)
    if user["role"] == "company":
        query = query.eq("company_id", user["id"])
    result = query.execute()
    return result.data