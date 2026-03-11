from fastapi import APIRouter, HTTPException
from app.database import supabase
from app.models import UserCreate, LoginRequest, LoginResponse
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register(user: UserCreate):
    try:
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not auth_response.user:
        raise HTTPException(status_code=400, detail="Registration failed")

    user_data = {
        "id": auth_response.user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "verified": False
    }
    supabase.table("users").insert(user_data).execute()

    if user.role == "student":
        student_profile = {
            "user_id": auth_response.user.id,
            "student_id": f"TEMP-{uuid.uuid4().hex[:8]}",
            "skills": []
        }
        supabase.table("student_profiles").insert(student_profile).execute()

    if user.role == "company":
        company_profile = {
            "user_id": auth_response.user.id,
            "company_name": user.full_name,
            "verified": False
        }
        supabase.table("company_profiles").insert(company_profile).execute()

    return {"message": "User created successfully", "user_id": auth_response.user.id}

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth_response.user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = supabase.table("users").select("role").eq("id", auth_response.user.id).single().execute()
    role = user.data["role"] if user.data else "student"

    return {
        "access_token": auth_response.session.access_token,
        "user_id": auth_response.user.id,
        "role": role
    }