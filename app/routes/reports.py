from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter()

# ============================================================
# GET reports
# ============================================================
@router.get("/")
async def get_reports(
    student_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    try:
        query = supabase.table("reports").select("*")
        
        if user.get("role") == "student":
            query = query.eq("student_id", user["id"])
        elif student_id:
            if user.get("role") != "admin" and user.get("id") != student_id:
                raise HTTPException(403, "Not authorized")
            query = query.eq("student_id", student_id)
        elif user.get("role") == "company":
            # Get company's interns
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if user_data.data and user_data.data[0].get("company_id"):
                company_id = user_data.data[0]["company_id"]
                students = supabase.table("users").select("id").eq("company_id", company_id).execute()
                student_ids = [s["id"] for s in students.data]
                if student_ids:
                    query = query.in_("student_id", student_ids)
                else:
                    return []
        
        result = query.order("date", desc=True).execute()
        
        # Enrich with student names
        for report in result.data:
            student = supabase.table("users").select("full_name").eq("id", report["student_id"]).execute()
            if student.data:
                report["student_name"] = student.data[0].get("full_name", "Unknown")
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return []

@router.get("")
async def get_reports_no_slash(
    student_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    return await get_reports(student_id, user)


# ============================================================
# POST submit report
# ============================================================
@router.post("/")
async def submit_report(
    date_str: str,
    title: str,
    description: str,
    hours: float,
    tasks: Optional[str] = None,
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
        "tasks": tasks or "",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        supabase.table("reports").insert(data).execute()
        return {"message": "Report submitted successfully"}
    except Exception as e:
        print(f"Error submitting report: {e}")
        raise HTTPException(500, str(e))

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


# ============================================================
# PATCH verify report (company approves/rejects)
# ============================================================
@router.patch("/{report_id}/verify")
async def verify_report(
    report_id: str,
    status: str,
    user=Depends(get_current_user)
):
    """Company verifies a student's report"""
    if user.get("role") not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    
    if status not in ["approved", "rejected"]:
        raise HTTPException(400, "Status must be 'approved' or 'rejected'")
    
    try:
        # Get the report
        report = supabase.table("reports").select("*").eq("id", report_id).execute()
        if not report.data:
            raise HTTPException(404, "Report not found")
        
        # If company user, verify this report belongs to their intern
        if user.get("role") == "company":
            user_data = supabase.table("users").select("company_id").eq("id", user["id"]).execute()
            if not user_data.data or not user_data.data[0].get("company_id"):
                raise HTTPException(403, "No company associated with your account")
            
            company_id = user_data.data[0]["company_id"]
            
            # Check if the student belongs to this company
            student = supabase.table("users").select("company_id").eq("id", report.data[0]["student_id"]).execute()
            if not student.data or student.data[0].get("company_id") != company_id:
                raise HTTPException(403, "This report does not belong to your intern")
        
        # Update report status
        supabase.table("reports").update({
            "status": status,
            "verified_by": user["id"],
            "verified_at": datetime.utcnow().isoformat()
        }).eq("id", report_id).execute()
        
        return {"message": f"Report {status} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying report: {e}")
        raise HTTPException(500, str(e))

# Handle without trailing slash
@router.patch("/{report_id}/verify")
async def verify_report_no_slash(
    report_id: str,
    status: str,
    user=Depends(get_current_user)
):
    return await verify_report(report_id, status, user)


# ============================================================
# GET single report by ID
# ============================================================
@router.get("/{report_id}")
async def get_report(report_id: str, user=Depends(get_current_user)):
    try:
        result = supabase.table("reports").select("*").eq("id", report_id).execute()
        if not result.data:
            raise HTTPException(404, "Report not found")
        
        report = result.data[0]
        
        if user.get("role") == "student" and report["student_id"] != user["id"]:
            raise HTTPException(403, "Not your report")
        
        return report
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching report: {e}")
        raise HTTPException(500, str(e))


# ============================================================
# DELETE report (admin only)
# ============================================================
@router.delete("/{report_id}")
async def delete_report(report_id: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    try:
        supabase.table("reports").delete().eq("id", report_id).execute()
        return {"message": "Report deleted"}
    except Exception as e:
        print(f"Error deleting report: {e}")
        raise HTTPException(500, str(e))
    
@router.patch("/{report_id}/verify")
async def verify_report(
    report_id: str,
    status: str,
    user=Depends(get_current_user)
):
    """Company verifies a student's report"""
    if user.get("role") not in ["company", "admin"]:
        raise HTTPException(403, "Not authorized")
    
    if status not in ["approved", "rejected"]:
        raise HTTPException(400, "Status must be 'approved' or 'rejected'")
    
    try:
        # Get the report
        report = supabase.table("reports").select("*").eq("id", report_id).execute()
        if not report.data:
            raise HTTPException(404, "Report not found")
        
        # Update report status
        supabase.table("reports").update({
            "status": status,
            "verified_by": user["id"],
            "verified_at": datetime.utcnow().isoformat()
        }).eq("id", report_id).execute()
        
        return {"message": f"Report {status} successfully"}
        
    except Exception as e:
        print(f"Error verifying report: {e}")
        raise HTTPException(500, str(e))

# Also add without trailing slash
@router.patch("/{report_id}/verify")
async def verify_report_no_slash(
    report_id: str,
    status: str,
    user=Depends(get_current_user)
):
    return await verify_report(report_id, status, user)

@router.patch("/{report_id}/verify/")
async def verify_report_trailing(
    report_id: str,
    status: str,
    user=Depends(get_current_user)
):
    return await verify_report(report_id, status, user)