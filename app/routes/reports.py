from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import date
from typing import Optional

router = APIRouter()

@router.post("/")
async def submit_report(
    date_str: str,
    title: str,
    description: str,
    hours: float,
    tasks: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Submit a daily report"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can submit reports")
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "date": date_str,
        "title": title,
        "description": description,
        "hours": hours,
        "tasks": tasks or "",
    }
    
    try:
        supabase.table("reports").insert(data).execute()
        return {"message": "Report submitted successfully"}
    except Exception as e:
        print(f"Error submitting report: {e}")
        raise HTTPException(500, f"Failed to submit report: {str(e)}")

# Also handle POST without trailing slash
@router.post("")
async def submit_report_no_slash(
    date_str: str,
    title: str,
    description: str,
    hours: float,
    tasks: Optional[str] = None,
    user=Depends(get_current_user)
):
    return await submit_report(date_str, title, description, hours, tasks, user)

@router.get("/")
async def get_reports(
    student_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get reports for a student"""
    try:
        query = supabase.table("reports").select("*")
        
        if student_id:
            if user.get("role") != "admin" and user.get("id") != student_id:
                raise HTTPException(403, "Not authorized")
            query = query.eq("student_id", student_id)
        elif user.get("role") == "student":
            query = query.eq("student_id", user["id"])
        
        result = query.order("date", desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return []