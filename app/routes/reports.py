from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.post("/")
async def submit_report(
    date_str: str,
    title: str,
    description: str,
    hours: float,
    tasks: str = None,
    user=Depends(get_current_user)
):
    if user.get("role") != "student":
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
        if user.get("role") != "admin" and user.get("id") != student_id:
            raise HTTPException(403, "Not authorized")
        query = query.eq("student_id", student_id)
    elif user.get("role") == "student":
        query = query.eq("student_id", user["id"])
    
    result = query.order("date", desc=True).execute()
    
    for report in result.data:
        student = supabase.table("users").select("full_name").eq("id", report["student_id"]).execute()
        if student.data:
            report["student_name"] = student.data[0].get("full_name", "Unknown")
    
    return result.data