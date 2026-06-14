from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.post("/")
async def log_attendance(
    student_id: str,
    date_str: str,
    hours_worked: float,
    status: str,
    task: str,
    user=Depends(get_current_user)
):
    if user.get("role") not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    
    # Validate input
    if not student_id:
        raise HTTPException(400, "student_id is required")
    if not date_str:
        raise HTTPException(400, "date_str is required")
    if status not in ["present", "half-day", "absent"]:
        raise HTTPException(400, "status must be 'present', 'half-day', or 'absent'")
    
    # Get company_id for the user
    company_id = None
    if user.get("role") == "company":
        user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
        if user_data.data:
            company_id = user_data.data[0].get("company_id")
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "company_id": company_id,
        "date": date_str,
        "hours_worked": hours_worked,
        "status": status,
        "task": task,
        "logged_by": user.get("full_name", user.get("email")),
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        result = supabase.table("attendance").insert(data).execute()
        return {"message": "Attendance logged", "attendance": result.data[0] if result.data else None}
    except Exception as e:
        print(f"Error logging attendance: {e}")
        raise HTTPException(500, str(e))

@router.post("")
async def log_attendance_no_slash(
    student_id: str,
    date_str: str,
    hours_worked: float,
    status: str,
    task: str,
    user=Depends(get_current_user)
):
    return await log_attendance(student_id, date_str, hours_worked, status, task, user)

@router.get("/")
async def get_attendance(
    student_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    try:
        query = supabase.table("attendance").select("*")
        
        # For students, always filter by their own ID
        if user.get("role") == "student":
            query = query.eq("student_id", user["id"])
        elif student_id:
            query = query.eq("student_id", student_id)
        elif user.get("role") == "company":
            # Get all students for this company
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if user_data.data and user_data.data[0].get("company_id"):
                company_id = user_data.data[0]["company_id"]
                # Get all student IDs for this company
                students = supabase.table("users").select("id").eq("company_id", company_id).execute()
                student_ids = [s["id"] for s in students.data]
                if student_ids:
                    query = query.in_("student_id", student_ids)
                else:
                    return []
        
        result = query.order("date", desc=True).execute()
        
        # Enrich with student names
        for record in result.data:
            student = supabase.table("users").select("full_name").eq("id", record["student_id"]).execute()
            if student.data:
                record["student_name"] = student.data[0].get("full_name", "Unknown")
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching attendance: {e}")
        return []

@router.get("")
async def get_attendance_no_slash(
    student_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    return await get_attendance(student_id, user)