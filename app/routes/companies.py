from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_companies(contact_email: str = None, user=Depends(get_current_user)):
    """Get companies, optionally filtered by contact_email"""
    query = supabase.table("companies").select("*")
    if contact_email:
        query = query.eq("contact_email", contact_email)
    result = query.execute()
    return result.data

@router.get("/{company_id}")
async def get_company(company_id: str, user=Depends(get_current_user)):
    result = supabase.table("companies").select("*").eq("id", company_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Company not found")
    return result.data