from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.database import supabase
from app.routes.auth import get_current_user
from app.ai_engine import vectorize_text
import uuid
from datetime import datetime
import io
import PyPDF2  # or from pypdf import PdfReader

router = APIRouter()

# Common skills to look for
COMMON_SKILLS = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP', 'Swift', 'Kotlin',
    'React', 'Angular', 'Vue', 'Next.js', 'Node.js', 'Express', 'Django', 'Flask', 'Spring Boot', 'FastAPI',
    'HTML', 'CSS', 'SASS', 'Tailwind CSS', 'Bootstrap', 'Material UI',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Firebase', 'Supabase', 'Prisma', 'TypeORM',
    'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'GitHub Actions', 'CI/CD',
    'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Matplotlib', 'Data Science', 'Machine Learning',
    'REST API', 'GraphQL', 'WebSocket', 'OAuth', 'JWT', 'Redis', 'RabbitMQ',
    'Agile', 'Scrum', 'Jira', 'Confluence', 'Leadership', 'Communication', 'Teamwork', 'Problem Solving'
]

def extract_skills_from_text(text):
    """Extract skills from resume text"""
    lower_text = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        if skill.lower() in lower_text:
            found.append(skill)
    return list(set(found))  # Remove duplicates

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
    
    # Extract text from PDF
    resume_text = ""
    extracted_skills = []
    
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        for page in pdf_reader.pages:
            resume_text += page.extract_text() or ""
        
        # Extract skills from resume text
        extracted_skills = extract_skills_from_text(resume_text)
        print(f"Extracted {len(extracted_skills)} skills from resume: {extracted_skills}")
        
    except Exception as e:
        print(f"PDF parsing error: {e}")
        # Continue without text extraction if PDF parsing fails
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_("documents").upload(file_name, file_content)
        file_url = supabase.storage.from_("documents").get_public_url(file_name)
        
        # Get current user skills
        current_user = supabase.table("users").select("skills").eq("id", user["id"]).execute()
        current_skills = current_user.data[0].get("skills", []) if current_user.data else []
        
        # Merge existing skills with extracted skills
        all_skills = list(set(current_skills + extracted_skills))
        
        # Generate AI embedding with combined skills and resume text
        text_for_embedding = " ".join(all_skills) + " " + resume_text[:5000]
        embedding = vectorize_text(text_for_embedding) if text_for_embedding.strip() else [0.0] * 384
        
        # Update user profile
        supabase.table("users").update({
            "resume_url": file_url,
            "skills": all_skills,
            "resume_text": resume_text[:10000] if resume_text else "",
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
        print(f"Resume upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")