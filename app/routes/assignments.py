from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from routes.auth import get_current_user, require_admin
import uuid
from datetime import datetime

router = APIRouter(prefix="/assignments", tags=["Assignments"])

@router.get("/")
async def get_assignments(
    student_id: str = None,
    company_id: str = None,
    faculty_id: str = None,
    user=Depends(get_current_user)
):
    query = supabase.table("assignments").select("*")
    
    if student_id:
        query = query.eq("student_id", student_id)
    if company_id:
        query = query.eq("company_id", company_id)
    if faculty_id:
        if user["role"] != "admin" and user["id"] != faculty_id:
            raise HTTPException(403, "Not authorized")
        query = query.eq("faculty_id", faculty_id)
    
    # If company user, only show their assignments
    if user["role"] == "company":
        query = query.eq("company_id", user["id"])
    
    result = query.execute()
    
    # Enrich with student names
    for assign in result.data:
        student = supabase.table("users").select("full_name, student_id, department, year").eq("id", assign["student_id"]).single().execute()
        if student.data:
            assign["student_name"] = student.data["full_name"]
            assign["roll_number"] = student.data.get("student_id", "")
            assign["department"] = student.data.get("department", "")
            assign["year"] = student.data.get("year", "")
    
    return result.data

@router.post("/")
async def create_assignment(assignment: dict, user=Depends(require_admin)):
    """Admin creates an assignment (company + student)"""
    data = {
        "id": str(uuid.uuid4()),
        "student_id": assignment["student_id"],
        "company_id": assignment["company_id"],
        "job_title": assignment.get("job_title"),
        "start_date": assignment.get("start_date"),
        "end_date": assignment.get("end_date"),
        "total_required_hours": assignment.get("total_required_hours", 480),
        "stipend": assignment.get("stipend"),
        "status": "active",
        "faculty_id": assignment.get("faculty_id"),
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("assignments").insert(data).execute()
    return {"message": "Assignment created", "assignment_id": result.data[0]["id"]}

@router.patch("/{assignment_id}")
async def update_assignment(assignment_id: str, updates: dict, user=Depends(get_current_user)):
    if user["role"] not in ["admin", "company"]:
        raise HTTPException(403, "Not authorized")
    
    allowed_fields = ["status", "end_date", "total_required_hours"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    
    supabase.table("assignments").update(filtered).eq("id", assignment_id).execute()
    return {"message": "Assignment updated"}