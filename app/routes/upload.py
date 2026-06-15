from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.database import supabase
from app.routes.auth import get_current_user
from app.ai_engine import vectorize_text, extract_skills_from_text
import uuid
from datetime import datetime
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload resume PDF, extract skills, and generate AI embedding"""
    if user.get("role") != "student":
        raise HTTPException(403, "Only students can upload resumes")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are allowed")
    
    # Read file content
    file_content = await file.read()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"resumes/{user['id']}_{timestamp}.pdf"
    
    # Try to extract text from PDF (if possible, otherwise use filename)
    resume_text = ""
    extracted_skills = []
    
    try:
        # For now, we'll use a simple extraction from filename and a note
        # In production, you'd want to use PyPDF2 or similar
        resume_text = f"Resume uploaded: {file.filename}"
        logger.info(f"Resume uploaded: {file.filename}")
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        resume_text = f"Resume file: {file.filename}"
    
    # Extract skills from filename and text
    extracted_skills = extract_skills_from_text(file.filename)
    logger.info(f"Extracted {len(extracted_skills)} skills from filename")
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_("documents").upload(file_name, file_content)
        file_url = supabase.storage.from_("documents").get_public_url(file_name)
        
        # Get current user skills
        current_user = supabase.table("users").select("skills").eq("id", user["id"]).execute()
        current_skills = current_user.data[0].get("skills", []) if current_user.data else []
        
        # Merge existing skills with extracted skills
        all_skills = list(set(current_skills + extracted_skills))
        
        # Generate AI embedding with combined skills
        text_for_embedding = " ".join(all_skills) + " " + resume_text[:1000]
        embedding = vectorize_text(text_for_embedding) if text_for_embedding.strip() else [0.0] * 64
        
        # Update user profile
        supabase.table("users").update({
            "resume_url": file_url,
            "skills": all_skills,
            "resume_text": resume_text[:5000] if resume_text else "",
            "skills_embedding": embedding,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user["id"]).execute()
        
        return {
            "message": "Resume uploaded successfully",
            "url": file_url,
            "extracted_skills": extracted_skills,
            "skills_count": len(all_skills),
            "embedding_generated": True
        }
    except Exception as e:
        logger.error(f"Resume upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/resume")
async def get_resume(user=Depends(get_current_user)):
    try:
        result = supabase.table("users").select("resume_url").eq("id", user["id"]).execute()
        return {"resume_url": result.data[0].get("resume_url") if result.data else None}
    except Exception:
        return {"resume_url": None}

@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    image_type: str = Form(...),
    user=Depends(get_current_user)
):
    """Upload profile picture or cover photo"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "Only image files are allowed")
    
    if image_type not in ['avatar', 'cover']:
        raise HTTPException(400, "image_type must be 'avatar' or 'cover'")
    
    file_content = await file.read()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    folder = "avatars" if image_type == "avatar" else "covers"
    file_name = f"{folder}/{user['id']}_{timestamp}.{file.filename.split('.')[-1]}"
    
    try:
        supabase.storage.from_("profile-images").upload(file_name, file_content)
        file_url = supabase.storage.from_("profile-images").get_public_url(file_name)
        
        if image_type == "avatar":
            supabase.table("users").update({"avatar_url": file_url}).eq("id", user["id"]).execute()
        else:
            supabase.table("users").update({"cover_url": file_url}).eq("id", user["id"]).execute()
        
        return {"message": f"{image_type.capitalize()} updated", "url": file_url}
    except Exception as e:
        logger.error(f"Profile image upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")