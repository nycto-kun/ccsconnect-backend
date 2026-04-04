from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# ---------- Existing models ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str
    student_id: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None

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

# ---------- New models for Resource Library ----------
class ResourceCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str  # guide, template, questions, papers, video, article
    category: Optional[str] = None
    tags: List[str] = []
    author: Optional[str] = None
    file_url: Optional[str] = None

class ResourceResponse(ResourceCreate):
    id: str
    download_count: int
    rating: float
    created_at: datetime
    updated_at: datetime

# ---------- New models for Offer Vault ----------
class OfferCreate(BaseModel):
    company: str
    role: str
    salary_range: Optional[str] = None
    location: Optional[str] = None
    benefits: List[str] = []
    file_url: Optional[str] = None

class OfferResponse(OfferCreate):
    id: str
    student_id: str
    status: str
    created_at: datetime

# ---------- New models for Chat ----------
class ConversationCreate(BaseModel):
    participant2_id: str

class ConversationResponse(BaseModel):
    id: str
    participant1_id: str
    participant2_id: str
    last_message: Optional[str] = None
    last_message_at: datetime
    other_user_name: Optional[str] = None
    other_user_avatar: Optional[str] = None

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: str
    sender_id: str
    content: str
    is_read: bool
    created_at: datetime

# ---------- New models for AI embeddings ----------
class SkillsEmbeddingRequest(BaseModel):
    skills: List[str]
    resume_text: Optional[str] = None

class JobEmbeddingRequest(BaseModel):
    title: str
    description: str
    requirements: List[str]

# ---------- Profile update ----------
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None