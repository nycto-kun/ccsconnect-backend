from fastapi import APIRouter
from app.database import supabase

router = APIRouter(prefix="/notices", tags=["Notices"])

@router.get("/")
async def get_notices():
    # Return empty list for now – you can add mock data later
    return []