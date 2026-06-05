from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def get_assignments(student_id: str = None, company_id: str = None, user=Depends(get_current_user)):
    query = supabase.table("assignments").select("*")
    
    if user.get("role") == "student":
        query = query.eq("student_id", user["id"])
    elif student_id:
        query = query.eq("student_id", student_id)
    elif company_id:
        query = query.eq("company_id", company_id)
    elif user.get("role") == "company":
        company = supabase.table("companies").select("id").eq("contact_email", user["email"]).single().execute()
        if company.data:
            query = query.eq("company_id", company.data["id"])
    
    result = query.execute()
    
    for assign in result.data:
        student = supabase.table("users").select("full_name, student_id, department").eq("id", assign["student_id"]).execute()
        if student.data:
            assign["student_name"] = student.data[0].get("full_name", "Unknown")
            assign["roll_number"] = student.data[0].get("student_id", "")
            assign["department"] = student.data[0].get("department", "")
    
    return result.data

@router.post("/")
async def create_assignment(assignment: dict, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    data = {
        "id": str(uuid.uuid4()),
        "student_id": assignment.get("student_id"),
        "company_id": assignment.get("company_id"),
        "job_title": assignment.get("job_title"),
        "start_date": assignment.get("start_date"),
        "end_date": assignment.get("end_date"),
        "total_required_hours": assignment.get("total_required_hours", 480),
        "stipend": assignment.get("stipend"),
        "status": "active",
    }
    result = supabase.table("assignments").insert(data).execute()
    return {"message": "Assignment created", "assignment": result.data[0]}

@router.patch("/{assignment_id}")
async def update_assignment(assignment_id: str, updates: dict, user=Depends(get_current_user)):
    if user.get("role") not in ["admin", "company"]:
        raise HTTPException(403, "Not authorized")
    
    allowed_fields = ["status", "end_date"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    
    supabase.table("assignments").update(filtered).eq("id", assignment_id).execute()
    return {"message": "Assignment updated"}