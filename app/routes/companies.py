from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.routes.auth import get_current_user
from typing import Optional

router = APIRouter()

# Handle both /companies and /companies/
@router.get("/")
@router.get("")
async def get_companies(
    contact_email: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get companies, optionally filtered by contact_email"""
    try:
        query = supabase.table("companies").select("*")
        if contact_email:
            query = query.eq("contact_email", contact_email)
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error in get_companies: {e}")
        return []

@router.get("/{company_id}")
async def get_company(company_id: str, user=Depends(get_current_user)):
    try:
        result = supabase.table("companies").select("*").eq("id", company_id).single().execute()
        if not result.data:
            raise HTTPException(404, "Company not found")
        return result.data
    except Exception as e:
        print(f"Error in get_company: {e}")
        raise HTTPException(500, str(e))