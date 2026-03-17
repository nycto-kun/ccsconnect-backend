import secrets
import string
from app.utils.email import send_temp_password_email

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.post("/register-student")
async def register_student(student_id: str, email: str):
    # 1. Check registrar_mock for matching student_id and email
    record = supabase.table("registrar_mock").select("*").eq("student_id", student_id).eq("email", email).maybe_single().execute()
    if not record.data:
        raise HTTPException(status_code=404, detail="No matching student record found")

    # 2. Generate a temporary password
    temp_password = generate_temp_password()

    # 3. Create user in Supabase Auth
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": temp_password,
            "options": {
                "data": {
                    "full_name": record.data["full_name"],
                    "role": "student"
                }
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
        "verified": False
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