from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_assignments(
    student_id: Optional[str] = None,
    company_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    try:
        query = supabase.table("assignments").select("*")
        
        if user.get("role") == "student":
            query = query.eq("student_id", user["id"])
        elif student_id:
            query = query.eq("student_id", student_id)
        elif company_id:
            query = query.eq("company_id", company_id)
        elif user.get("role") == "company":
            # Get company_id from user
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if user_data.data and user_data.data[0].get("company_id"):
                query = query.eq("company_id", user_data.data[0]["company_id"])
            else:
                return []
        
        result = query.execute()
        
        # Enrich with student names
        for assign in result.data:
            student = supabase.table("users").select("full_name, student_id, email").eq("id", assign["student_id"]).execute()
            if student.data:
                assign["student_name"] = student.data[0].get("full_name", "Unknown")
                assign["roll_number"] = student.data[0].get("student_id", "")
                assign["student_email"] = student.data[0].get("email", "")
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching assignments: {e}")
        return []

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
    return {"message": "Assignment created", "assignment": result.data[0] if result.data else data}

@router.patch("/{assignment_id}")
async def update_assignment(assignment_id: str, updates: dict, user=Depends(get_current_user)):
    if user.get("role") not in ["admin", "company"]:
        raise HTTPException(403, "Not authorized")
    
    allowed_fields = ["status", "end_date"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    
    supabase.table("assignments").update(filtered).eq("id", assignment_id).execute()
    return {"message": "Assignment updated"}

@router.get("/company/interns")
async def get_company_interns(user=Depends(get_current_user)):
    """Get all interns (students) assigned to the logged-in company"""
    if user.get("role") != "company":
        raise HTTPException(403, "Only company users can access this endpoint")
    
    try:
        # Get company_id from user profile
        user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
        if not user_data.data or not user_data.data[0].get("company_id"):
            return []
        
        company_id = user_data.data[0]["company_id"]
        
        # Get all students assigned to this company via assignments
        result = supabase.table("assignments").select("*, users!inner(full_name, email, student_id, department, year)").eq("company_id", company_id).execute()
        
        interns = []
        for item in result.data:
            interns.append({
                "id": item["student_id"],
                "student_name": item["users"]["full_name"],
                "email": item["users"]["email"],
                "roll_number": item["users"]["student_id"],
                "department": item["users"]["department"],
                "year": item["users"]["year"],
                "job_title": item["job_title"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "total_required_hours": item["total_required_hours"],
                "stipend": item["stipend"],
                "status": item["status"]
            })
        
        return interns
    except Exception as e:
        print(f"Error fetching company interns: {e}")
        return []

# Also add trailing slash version
@router.get("/company/interns/")
async def get_company_interns_trailing(user=Depends(get_current_user)):
    return await get_company_interns(user)