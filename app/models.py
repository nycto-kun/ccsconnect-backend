from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # 'student', 'company', 'admin'

class StudentProfileCreate(BaseModel):
    user_id: str
    student_id: str
    course: Optional[str] = None
    year_level: Optional[int] = None
    skills: List[str] = []
    resume_text: Optional[str] = ""
    gpa: Optional[float] = None

class CompanyProfileCreate(BaseModel):
    user_id: str
    company_name: str
    industry: Optional[str] = None
    contact_person: Optional[str] = None

class JobCreate(BaseModel):
    company_id: str
    title: str
    description: str
    requirements: List[str] = []
    location: Optional[str] = None
    salary_range: Optional[str] = None
    duration: Optional[str] = None
    expires_at: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    role: str