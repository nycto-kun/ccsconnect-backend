from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import supabase
from app.models import UserCreate, LoginRequest, LoginResponse
from app.utils.email import send_temp_password_email
import uuid
import secrets
import string

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------- NEW: Student registration using registrar data ----------
@router.post("/register-student")
async def register_student(student_id: str, email: str):
    # 1. Check registrar_mock for matching student_id and email
    record = supabase.table("registrar_mock").select("*").eq("student_id", student_id).eq("email", email).maybe_single().execute()
    if not record.data:
        raise HTTPException(status_code=404, detail="No matching student record found")

    # 2. Generate a temporary password
    temp_password = generate_temp_password()

    # 3. Create user using Admin API (bypasses confirmation email)
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,          # mark as confirmed so they can log in immediately
            "user_metadata": {
                "full_name": record.data["full_name"],
                "role": "student"
            }
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

    if not auth_response.user:
        raise HTTPException(status_code=400, detail="User creation failed")

    # 4. Insert into public.users table
    user_data = {
        "id": auth_response.user.id,
        "email": email,
        "full_name": record.data["full_name"],
        "role": "student",
        "verified": True
    }
    supabase.table("users").insert(user_data).execute()

    # 5. Create student profile with registrar data
    student_profile = {
        "user_id": auth_response.user.id,
        "student_id": student_id,
        "course": record.data.get("course"),
        "year_level": record.data.get("year_level"),
        "gpa": record.data.get("gpa"),
        "skills": []
    }
    supabase.table("student_profiles").insert(student_profile).execute()

    # 6. Send email with temporary password
    await send_temp_password_email(email, temp_password)

    return {"message": "Account created. Please check your email for the temporary password."}

# ---------- EXISTING ENDPOINTS (unchanged) ----------

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
        student_id_provided = user.student_id
        if student_id_provided:
            registrar = supabase.table("registrar_mock").select("*").eq("student_id", student_id_provided).maybe_single().execute()
            if registrar.data:
                student_profile = {
                    "user_id": auth_response.user.id,
                    "student_id": student_id_provided,
                    "course": registrar.data.get("course"),
                    "year_level": registrar.data.get("year_level"),
                    "gpa": registrar.data.get("gpa"),
                    "skills": []
                }
            else:
                student_profile = {
                    "user_id": auth_response.user.id,
                    "student_id": f"TEMP-{uuid.uuid4().hex[:8]}",
                    "skills": []
                }
        else:
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

@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        profile = supabase.table("users").select("*").eq("id", user.user.id).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="User not found in database")
        return profile.data
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")