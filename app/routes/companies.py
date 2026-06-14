from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import supabase
from app.routes.auth import get_current_user
from typing import Optional
import uuid

router = APIRouter()

@router.get("/")
async def get_companies(
    contact_email: Optional[str] = Query(None),
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
    """Get a single company by ID"""
    try:
        result = supabase.table("companies").select("*").eq("id", company_id).execute()
        if not result.data:
            raise HTTPException(404, "Company not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_company: {e}")
        raise HTTPException(500, str(e))

# Handle trailing slash
@router.get("/{company_id}/")
async def get_company_trailing(company_id: str, user=Depends(get_current_user)):
    """Handle /companies/{id}/ with trailing slash"""
    return await get_company(company_id, user)