from fastapi import APIRouter

router = APIRouter(prefix="/announcements", tags=["Announcements"])

@router.get("/")
async def get_announcements():
    return []