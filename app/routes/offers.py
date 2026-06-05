from fastapi import APIRouter, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def get_offers(user=Depends(get_current_user)):
    result = supabase.table("offers").select("*").eq("student_id", user["id"]).execute()
    return result.data

@router.post("/")
async def create_offer(offer: dict, user=Depends(get_current_user)):
    data = {
        "id": str(uuid.uuid4()),
        "student_id": user["id"],
        "company": offer.get("company"),
        "role": offer.get("role"),
        "salary_range": offer.get("salary_range"),
        "location": offer.get("location"),
        "status": "pending"
    }
    result = supabase.table("offers").insert(data).execute()
    return result.data[0]