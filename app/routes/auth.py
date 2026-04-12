from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import supabase
from app.models import UserCreate, LoginRequest, LoginResponse, ProfileUpdate
from app.utils.email import send_verification_email, send_temp_password_email
import uuid
import secrets
import string
from datetime import datetime, timedelta, timezone
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------- Student registration (only sends verification link) ----------
@router.post("/register-student")
async def register_student(student_id: str, email: str):
    # 1. Check registrar_mock
    record = supabase.table("registrar_mock").select("*").eq("student_id", student_id).eq("email", email).maybe_single().execute()
    if not record.data:
        raise HTTPException(status_code=404, detail="No matching student record found")

    # 2. Generate unique token
    token = secrets.token_urlsafe(32)

    # 3. Store in pending_registrations (use timezone-aware datetime)
    pending_data = {
        "student_id": student_id,
        "email": email,
        "full_name": record.data["full_name"],
        "course": record.data.get("course"),
        "year_level": record.data.get("year_level"),
        "gpa": record.data.get("gpa"),
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "used": False
    }
    supabase.table("pending_registrations").insert(pending_data).execute()

    # 4. Send verification email
    frontend_url = os.getenv("FRONTEND_URL", "https://ccsconnect-frontend.vercel.app")
    verification_link = f"{frontend_url}/verify-registration?token={token}"
    await send_verification_email(email, verification_link, record.data["full_name"])

    return {"message": "Verification link sent to your email. Please click it to complete registration."}

# ---------- Verify registration and create account ----------
@router.post("/verify-registration")
async def verify_registration(token: str):
    # 1. Look up token
    pending = supabase.table("pending_registrations").select("*").eq("token", token).maybe_single().execute()
    if not pending.data:
        raise HTTPException(404, "Invalid token")
    if pending.data["used"]:
        raise HTTPException(400, "Token already used")

    # 2. Check expiration (timezone-aware comparison)
    expires_at = datetime.fromisoformat(pending.data["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired")

    # 3. Mark token as used
    supabase.table("pending_registrations").update({"used": True}).eq("token", token).execute()

    # 4. Generate temporary password
    temp_password = generate_temp_password()
    full_name = pending.data["full_name"]

    # 5. Create user in Supabase Auth
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": pending.data["email"],
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "role": "student"
            }
        })
    except Exception as e:
        raise HTTPException(400, detail=f"Failed to create user: {str(e)}")

    if not auth_response.user:
        raise HTTPException(400, detail="User creation failed")

    # 6. Insert into users table
    user_data = {
        "id": auth_response.user.id,
        "email": pending.data["email"],
        "full_name": full_name,
        "role": "student",
        "verified": True,
        "student_id": pending.data["student_id"],
        "department": pending.data["course"],
        "year": pending.data["year_level"],
        "gpa": pending.data["gpa"],
        "skills": []
    }
    supabase.table("users").insert(user_data).execute()

    # 7. Send email with temporary password
    await send_temp_password_email(pending.data["email"], temp_password, full_name)

    return {"message": "Account created. Check your email for the temporary password."}

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

    if user.role == "company":
        # Create company in companies table
        company_data = {
            "name": user.company_name or user.full_name,
            "company_code": f"COMP-{uuid.uuid4().hex[:8]}",
            "verified": False,
            "contact_email": user.email,
        }
        company_result = supabase.table("companies").insert(company_data).execute()
        if company_result.data:
            company_id = company_result.data[0]["id"]
            user_data["company_id"] = company_id
            user_data["company_name"] = user.company_name
            user_data["industry"] = user.industry

    supabase.table("users").insert(user_data).execute()
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

# ---------- Forgot password ----------
@router.post("/forgot-password")
async def forgot_password(email: str):
    try:
        await supabase.auth.reset_password_for_email(email)
        return {"message": "If an account exists with that email, a password reset link has been sent."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Change password ----------
@router.post("/change-password")
async def change_password(old_password: str, new_password: str, user=Depends(get_current_user)):
    try:
        supabase.auth.sign_in_with_password({
            "email": user["email"],
            "password": old_password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Old password is incorrect")
    try:
        supabase.auth.admin.update_user_by_id(user["id"], {"password": new_password})
        return {"message": "Password changed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")