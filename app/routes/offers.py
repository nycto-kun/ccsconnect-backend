from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.models import OfferCreate, OfferResponse
from app.routes.auth import get_current_user, require_admin
from typing import List
import uuid

router = APIRouter(prefix="/offers", tags=["Offers"])

@router.get("/", response_model=List[OfferResponse])
async def get_my_offers(user=Depends(get_current_user)):
    result = supabase.table("offers").select("*").eq("student_id", user["id"]).execute()
    return result.data

@router.post("/", response_model=OfferResponse)
async def create_offer(offer: OfferCreate, user=Depends(get_current_user)):
    data = offer.dict()
    data["student_id"] = user["id"]
    data["status"] = "pending"
    data["id"] = str(uuid.uuid4())
    result = supabase.table("offers").insert(data).execute()
    if not result.data:
        raise HTTPException(400, "Failed to create offer")
    return result.data[0]

@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(offer_id: str, user=Depends(get_current_user)):
    result = supabase.table("offers").select("*").eq("id", offer_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Offer not found")
    if result.data["student_id"] != user["id"]:
        raise HTTPException(403, "Not your offer")
    return result.data

@router.delete("/{offer_id}")
async def delete_offer(offer_id: str, user=Depends(get_current_user)):
    offer = supabase.table("offers").select("student_id").eq("id", offer_id).single().execute()
    if not offer.data:
        raise HTTPException(404, "Offer not found")
    if offer.data["student_id"] != user["id"]:
        raise HTTPException(403, "Not your offer")
    supabase.table("offers").delete().eq("id", offer_id).execute()
    return {"message": "Deleted"}

@router.get("/admin/pending", dependencies=[Depends(require_admin)], response_model=List[OfferResponse])
async def get_pending_offers():
    result = supabase.table("offers").select("*").eq("status", "pending").execute()
    return result.data

@router.post("/admin/verify/{offer_id}", dependencies=[Depends(require_admin)])
async def verify_offer(offer_id: str):
    supabase.table("offers").update({"status": "verified"}).eq("id", offer_id).execute()
    return {"message": "Offer verified"}