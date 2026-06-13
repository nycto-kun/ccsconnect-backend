from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from typing import Optional

router = APIRouter()

# ============================================================
# RESUME UPLOAD
# ============================================================
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
    
    # Read file content
    file_content = await file.read()
    
    # Generate unique filename
    file_ext = file.filename.split('.')[-1]
    file_name = f"resumes/{user['id']}_{uuid.uuid4().hex}.{file_ext}"
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_("documents").upload(file_name, file_content)
        file_url = supabase.storage.from_("documents").get_public_url(file_name)
        
        # Update user profile
        supabase.table("users").update({"resume_url": file_url}).eq("id", user["id"]).execute()
        
        return {
            "message": "Resume uploaded successfully", 
            "url": file_url,
            "filename": file.filename
        }
    except Exception as e:
        print(f"Resume upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/resume")
async def get_resume(user=Depends(get_current_user)):
    """Get resume URL for current user"""
    try:
        result = supabase.table("users").select("resume_url").eq("id", user["id"]).single().execute()
        return {"resume_url": result.data.get("resume_url") if result.data else None}
    except Exception as e:
        return {"resume_url": None}

@router.delete("/resume")
async def delete_resume(user=Depends(get_current_user)):
    """Delete resume"""
    try:
        supabase.table("users").update({"resume_url": None}).eq("id", user["id"]).execute()
        return {"message": "Resume deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


# ============================================================
# PROFILE IMAGE UPLOAD (Avatar & Cover)
# ============================================================
@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    image_type: str = Form(...),  # 'avatar' or 'cover'
    user=Depends(get_current_user)
):
    """Upload profile picture (avatar) or cover photo"""
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "Only image files are allowed")
    
    # Validate image type parameter
    if image_type not in ['avatar', 'cover']:
        raise HTTPException(400, "image_type must be 'avatar' or 'cover'")
    
    # Read file content
    file_content = await file.read()
    
    # Generate unique filename
    file_ext = file.filename.split('.')[-1]
    folder = "avatars" if image_type == "avatar" else "covers"
    file_name = f"{folder}/{user['id']}_{uuid.uuid4().hex}.{file_ext}"
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_("profile-images").upload(file_name, file_content)
        file_url = supabase.storage.from_("profile-images").get_public_url(file_name)
        
        # Update user profile
        if image_type == "avatar":
            supabase.table("users").update({"avatar_url": file_url}).eq("id", user["id"]).execute()
        else:
            supabase.table("users").update({"cover_url": file_url}).eq("id", user["id"]).execute()
        
        return {
            "message": f"{image_type.capitalize()} updated successfully",
            "url": file_url,
            "type": image_type
        }
    except Exception as e:
        print(f"Profile image upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/profile-image")
async def get_profile_images(user=Depends(get_current_user)):
    """Get avatar and cover URLs for current user"""
    try:
        result = supabase.table("users").select("avatar_url, cover_url").eq("id", user["id"]).single().execute()
        return {
            "avatar_url": result.data.get("avatar_url") if result.data else None,
            "cover_url": result.data.get("cover_url") if result.data else None
        }
    except Exception as e:
        return {"avatar_url": None, "cover_url": None}

@router.delete("/profile-image")
async def delete_profile_image(
    image_type: str,
    user=Depends(get_current_user)
):
    """Delete avatar or cover photo"""
    if image_type not in ['avatar', 'cover']:
        raise HTTPException(400, "image_type must be 'avatar' or 'cover'")
    
    try:
        if image_type == "avatar":
            supabase.table("users").update({"avatar_url": None}).eq("id", user["id"]).execute()
        else:
            supabase.table("users").update({"cover_url": None}).eq("id", user["id"]).execute()
        
        return {"message": f"{image_type.capitalize()} deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")