from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.models import ResourceCreate, ResourceResponse
from app.routes.auth import require_admin
from typing import List, Optional
import uuid

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("/", response_model=List[ResourceResponse])
async def get_resources(
    type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    query = supabase.table("resources").select("*")
    if type:
        query = query.eq("type", type)
    if category:
        query = query.eq("category", category)
    if search:
        query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%,tags.cs.{{{search}}}")
    result = query.range(offset, offset + limit - 1).execute()
    return result.data

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str):
    result = supabase.table("resources").select("*").eq("id", resource_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Resource not found")
    return result.data

@router.post("/", response_model=ResourceResponse, dependencies=[Depends(require_admin)])
async def create_resource(resource: ResourceCreate):
    data = resource.dict()
    data["id"] = str(uuid.uuid4())
    result = supabase.table("resources").insert(data).execute()
    if not result.data:
        raise HTTPException(400, "Failed to create resource")
    return result.data[0]

@router.post("/{resource_id}/download")
async def increment_download_count(resource_id: str):
    resource = supabase.table("resources").select("download_count").eq("id", resource_id).single().execute()
    if not resource.data:
        raise HTTPException(404, "Resource not found")
    new_count = resource.data["download_count"] + 1
    supabase.table("resources").update({"download_count": new_count}).eq("id", resource_id).execute()
    return {"message": "Download counted"}

@router.delete("/{resource_id}", dependencies=[Depends(require_admin)])
async def delete_resource(resource_id: str):
    result = supabase.table("resources").delete().eq("id", resource_id).execute()
    if not result.data:
        raise HTTPException(404, "Resource not found")
    return {"message": "Deleted"}