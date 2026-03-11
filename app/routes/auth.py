from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import supabase
from app.models import UserCreate, LoginRequest, LoginResponse
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

@router.post("/register")
async def register(user: UserCreate):
    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not auth_response.user:
        raise HTTPException(status_code=400, detail="Registration failed")

    # Insert into public.users table
    user_data = {
        "id": auth_response.user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "verified": False
    }
    supabase.table("users").insert(user_data).execute()

    # Create role-specific profile
    if user.role == "student":
        student_id_provided = user.student_id
        if student_id_provided:
            # Look up in registrar_mock
            registrar = supabase.table("registrar_mock").select("*").eq("student_id", student_id_provided).maybe_single().execute()
            if registrar.data:
                # Use registrar data to create full profile
                student_profile = {
                    "user_id": auth_response.user.id,
                    "student_id": student_id_provided,
                    "course": registrar.data.get("course"),
                    "year_level": registrar.data.get("year_level"),
                    "gpa": registrar.data.get("gpa"),
                    "skills": []
                }
            else:
                # Registrar record not found – create temporary profile
                student_profile = {
                    "user_id": auth_response.user.id,
                    "student_id": f"TEMP-{uuid.uuid4().hex[:8]}",
                    "skills": []
                }
        else:
            # No student_id provided – fallback to temporary
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

    # Fetch user role from public.users table
    user = supabase.table("users").select("role").eq("id", auth_response.user.id).single().execute()
    role = user.data["role"] if user.data else "student"

    return {
        "access_token": auth_response.session.access_token,
        "user_id": auth_response.user.id,
        "role": role
    }

@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token)
        # Fetch full user profile from public.users table
        profile = supabase.table("users").select("*").eq("id", user.user.id).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="User not found in database")
        return profile.data
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")