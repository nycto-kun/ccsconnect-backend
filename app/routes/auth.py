from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import supabase
from app.models import UserCreate, LoginRequest, LoginResponse, ProfileUpdate
from app.utils.email import send_temp_password_email
import uuid
import secrets
import string

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------- Student registration using registrar data ----------
@router.post("/register-student")
async def register_student(student_id: str, email: str):
    record = supabase.table("registrar_mock").select("*").eq("student_id", student_id).eq("email", email).maybe_single().execute()
    if not record.data:
        raise HTTPException(status_code=404, detail="No matching student record found")

    temp_password = generate_temp_password()

    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": record.data["full_name"],
                "role": "student"
            }
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

    if not auth_response.user:
        raise HTTPException(status_code=400, detail="User creation failed")

    user_data = {
        "id": auth_response.user.id,
        "email": email,
        "full_name": record.data["full_name"],
        "role": "student",
        "verified": True
    }
    supabase.table("users").insert(user_data).execute()

    student_profile = {
        "user_id": auth_response.user.id,
        "student_id": student_id,
        "course": record.data.get("course"),
        "year_level": record.data.get("year_level"),
        "gpa": record.data.get("gpa"),
        "skills": []
    }
    supabase.table("student_profiles").insert(student_profile).execute()

    await send_temp_password_email(email, temp_password)
    return {"message": "Account created. Please check your email for the temporary password."}

# ---------- General registration (companies, admins, manual students) ----------
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
            "company_name": user.company_name or user.full_name,
            "industry": user.industry,
            "verified": False
        }
        supabase.table("company_profiles").insert(company_profile).execute()

    return {"message": "User created successfully", "user_id": auth_response.user.id}

# ---------- Login ----------
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

# ---------- Get current user ----------
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

# ---------- Profile update ----------
@router.put("/profile")
async def update_profile(updates: ProfileUpdate, user=Depends(get_current_user)):
    allowed_fields = ["full_name", "phone", "location", "bio", "github", "linkedin", "portfolio", "department", "year"]
    filtered = {k: v for k, v in updates.dict(exclude_unset=True).items() if k in allowed_fields}
    if not filtered:
        raise HTTPException(400, "No valid fields to update")
    supabase.table("users").update(filtered).eq("id", user["id"]).execute()
    return {"message": "Profile updated"}

# ---------- Admin dependency ----------
async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user

# ========== NEW ENDPOINTS ==========

# ---------- Forgot password (reset link) ----------
@router.post("/forgot-password")
async def forgot_password(email: str):
    try:
        # Supabase sends a password reset email to the user's email address
        # The reset link will redirect to your frontend (configured in Supabase Auth settings)
        await supabase.auth.reset_password_for_email(email)
        return {"message": "If an account exists with that email, a password reset link has been sent."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Change password (while logged in) ----------
@router.post("/change-password")
async def change_password(old_password: str, new_password: str, user=Depends(get_current_user)):
    # First verify the old password by attempting to sign in
    try:
        supabase.auth.sign_in_with_password({
            "email": user["email"],
            "password": old_password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    # Update the user's password using admin API (requires service role key)
    try:
        supabase.auth.admin.update_user_by_id(user["id"], {"password": new_password})
        return {"message": "Password changed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")