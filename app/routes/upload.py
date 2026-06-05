from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from database import supabase
from routes.auth import get_current_user
import uuid

router = APIRouter()

@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload resume PDF"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can upload resumes")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are allowed")
    
    file_content = await file.read()
    file_name = f"{user['id']}_{uuid.uuid4().hex}.pdf"
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_("resumes").upload(file_name, file_content)
        file_url = supabase.storage.from_("resumes").get_public_url(file_name)
        
        # Update user profile
        supabase.table("users").update({"resume_url": file_url}).eq("id", user["id"]).execute()
        
        return {"message": "Resume uploaded successfully", "url": file_url}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/resume")
async def get_resume(user=Depends(get_current_user)):
    """Get resume URL for current user"""
    result = supabase.table("users").select("resume_url").eq("id", user["id"]).single().execute()
    return {"resume_url": result.data.get("resume_url") if result.data else None}