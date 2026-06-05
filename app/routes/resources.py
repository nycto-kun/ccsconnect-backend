from fastapi import APIRouter, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def get_resources(type: str = None):
    query = supabase.table("resources").select("*")
    if type:
        query = query.eq("type", type)
    result = query.execute()
    return result.data