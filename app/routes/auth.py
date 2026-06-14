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

router = APIRouter()
security = HTTPBearer()

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------- Student registration ----------
@router.post("/register-student")
async def register_student(student_id: str, email: str):
    # Check registrar_mock
    record = supabase.table("registrar_mock").select("*").eq("student_id", student_id).eq("email", email).maybe_single().execute()
    if not record.data:
        raise HTTPException(status_code=404, detail="No matching student record found")

    # Check if already registered
    existing = supabase.table("users").select("*").eq("email", email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate token
    token = secrets.token_urlsafe(32)

    # Store pending registration
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

    # Send verification email
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    verification_link = f"{frontend_url}/verify-registration?token={token}"
    await send_verification_email(email, verification_link, record.data["full_name"])

    return {"message": "Verification link sent to your email"}

# ---------- Verify registration ----------
@router.post("/verify-registration")
async def verify_registration(token: str):
    pending = supabase.table("pending_registrations").select("*").eq("token", token).maybe_single().execute()
    if not pending.data:
        raise HTTPException(404, "Invalid token")
    if pending.data["used"]:
        raise HTTPException(400, "Token already used")

    expires_at = datetime.fromisoformat(pending.data["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired")

    supabase.table("pending_registrations").update({"used": True}).eq("token", token).execute()

    temp_password = generate_temp_password()
    full_name = pending.data["full_name"]

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

    user_data = {
        "id": auth_response.user.id,
        "email": pending.data["email"],
        "full_name": full_name,
        "role": "student",
        "verified": True,
        "student_id": pending.data["student_id"],
        "department": pending.data["course"],
        "year": str(pending.data["year_level"]) if pending.data["year_level"] else None,
        "gpa": pending.data["gpa"],
        "skills": []
    }
    supabase.table("users").insert(user_data).execute()

    await send_temp_password_email(pending.data["email"], temp_password, full_name)

    return {"message": "Account created. Check your email for the temporary password."}

# ---------- Company registration ----------
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
        company_data = {
            "id": str(uuid.uuid4()),
            "name": user.company_name or user.full_name,
            "company_code": f"COMP-{uuid.uuid4().hex[:8]}",
            "verified": False,
            "contact_email": user.email,
            "industry": user.industry,
        }
        company_result = supabase.table("companies").insert(company_data).execute()
        if company_result.data:
            user_data["company_id"] = company_result.data[0]["id"]

    supabase.table("users").insert(user_data).execute()
    return {"message": "User created successfully. Please check your email for verification.", "user_id": auth_response.user.id}

# ---------- Login ----------
@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth_response.user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Use try/except to handle RLS issues gracefully
    try:
        user = supabase.table("users").select("role, company_id").eq("id", auth_response.user.id).single().execute()
        role = user.data["role"] if user.data else "student"
        company_id = user.data.get("company_id") if user.data else None
    except Exception as e:
        print(f"Error fetching user role: {e}")
        role = "student"
        company_id = None

    return {
        "access_token": auth_response.session.access_token,
        "user_id": auth_response.user.id,
        "role": role,
        "company_id": company_id
    }

# ---------- Get current user ----------
@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        profile = supabase.table("users").select("*").eq("id", user.user.id).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="User not found")
        return profile.data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------- Profile update ----------
@router.put("/profile")
async def update_profile(updates: dict, user=Depends(get_current_user)):
    allowed_fields = ["full_name", "phone", "location", "bio", "github", "linkedin", "portfolio", "department", "year", "skills"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    
    if not filtered:
        raise HTTPException(400, "No valid fields to update")
    
    result = supabase.table("users").update(filtered).eq("id", user["id"]).execute()
    
    # Return updated user
    updated_user = supabase.table("users").select("*").eq("id", user["id"]).single().execute()
    return updated_user.data if updated_user.data else {"message": "Profile updated"}

# ---------- Forgot password ----------
@router.post("/forgot-password")
async def forgot_password(email: str):
    try:
        user = supabase.table("users").select("*").eq("email", email).execute()
        if user.data:
            supabase.auth.reset_password_for_email(email)
        return {"message": "If an account exists, a password reset link has been sent."}
    except Exception:
        return {"message": "If an account exists, a password reset link has been sent."}

# ---------- Change password ----------
@router.post("/change-password")
async def change_password(
    old_password: str, 
    new_password: str, 
    user=Depends(get_current_user)
):
    try:
        # Verify old password
        supabase.auth.sign_in_with_password({
            "email": user["email"],
            "password": old_password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Old password is incorrect")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    try:
        supabase.auth.admin.update_user_by_id(user["id"], {"password": new_password})
        return {"message": "Password changed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")

# ---------- Admin dependency ----------
async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user

@router.put("/preferences")
async def update_preferences(preferences: dict, user=Depends(get_current_user)):
    """Update user notification preferences"""
    supabase.table("users").update({"preferences": preferences}).eq("id", user["id"]).execute()
    return {"message": "Preferences updated"}

@router.put("/privacy")
async def update_privacy(privacy: dict, user=Depends(get_current_user)):
    """Update user privacy settings"""
    supabase.table("users").update({"privacy_settings": privacy}).eq("id", user["id"]).execute()
    return {"message": "Privacy settings updated"}

@router.put("/profile-with-embedding")
async def update_profile_with_embedding(updates: dict, user=Depends(get_current_user)):
    """Update profile and regenerate AI embedding"""
    allowed_fields = ["full_name", "phone", "location", "bio", "github", "linkedin", "portfolio", "department", "year", "skills"]
    filtered = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    
    if not filtered:
        raise HTTPException(400, "No valid fields to update")
    
    supabase.table("users").update(filtered).eq("id", user["id"]).execute()
    
    # Regenerate embedding if skills were updated
    if "skills" in filtered and user.get("role") == "student":
        try:
            from app.ai_engine import vectorize_text
            skills = filtered["skills"]
            text = " ".join(skills)
            embedding = vectorize_text(text)
            supabase.table("users").update({"skills_embedding": embedding}).eq("id", user["id"]).execute()
        except Exception as e:
            print(f"Embedding update failed: {e}")
    
    updated_user = supabase.table("users").select("*").eq("id", user["id"]).single().execute()
    return updated_user.data if updated_user.data else {"message": "Profile updated"}