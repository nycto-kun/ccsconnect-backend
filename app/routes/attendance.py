from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

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
    
    company_id = None
    if user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).single().execute()
        company_id = company.data["id"] if company.data else None
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "company_id": company_id,
        "date": date_str,
        "hours_worked": hours_worked,
        "status": status,
        "task": task,
        "logged_by": user.get("full_name", user.get("email")),
    }
    supabase.table("attendance").insert(data).execute()
    return {"message": "Attendance logged"}

@router.get("/")
async def get_attendance(student_id: str = None, user=Depends(get_current_user)):
    query = supabase.table("attendance").select("*")
    
    if student_id:
        query = query.eq("student_id", student_id)
    elif user.get("role") == "student":
        query = query.eq("student_id", user["id"])
    elif user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).single().execute()
        if company.data:
            query = query.eq("company_id", company.data["id"])
    
    result = query.order("date", desc=True).execute()
    
    for record in result.data:
        student = supabase.table("users").select("full_name").eq("id", record["student_id"]).execute()
        if student.data:
            record["student_name"] = student.data[0].get("full_name", "Unknown")
    
    return result.data