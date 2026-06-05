from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import date

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.post("/")
async def submit_report(
    date_str: str,
    title: str,
    description: str,
    hours: float,
    tasks: str = None,
    user=Depends(get_current_user)
):
    if user["role"] != "student":
        raise HTTPException(403, "Only students can submit reports")
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "date": date_str,
        "title": title,
        "description": description,
        "hours": hours,
        "tasks": tasks,
    }
    supabase.table("reports").insert(data).execute()
    return {"message": "Report submitted"}

@router.get("/")
async def get_reports(student_id: str = None, user=Depends(get_current_user)):
    query = supabase.table("reports").select("*")
    if student_id:
        if user["role"] != "student" or user["id"] != student_id:
            # Admin or faculty can view any student's reports
            if user["role"] not in ["admin", "faculty"]:
                raise HTTPException(403, "Not authorized")
        query = query.eq("student_id", student_id)
    else:
        # If no student_id, return own reports (for students) or all (for admin)
        if user["role"] == "student":
            query = query.eq("student_id", user["id"])
        elif user["role"] == "faculty":
            # For faculty, get reports of assigned students (simplified: all)
            pass
    result = query.execute()
    return result.data