from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.routes.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/conversations")
async def get_conversations(user=Depends(get_current_user)):
    convs1 = supabase.table("conversations").select("*").eq("participant1_id", user["id"]).execute()
    convs2 = supabase.table("conversations").select("*").eq("participant2_id", user["id"]).execute()
    conversations = convs1.data + convs2.data
    
    for conv in conversations:
        other_id = conv["participant2_id"] if conv["participant1_id"] == user["id"] else conv["participant1_id"]
        other = supabase.table("users").select("full_name").eq("id", other_id).single().execute()
        conv["other_user_name"] = other.data["full_name"] if other.data else "Unknown"
    
    return conversations

@router.post("/conversations")
async def create_conversation(participant2_id: str, user=Depends(get_current_user)):
    existing = supabase.table("conversations").select("*").or_(
        f"and(participant1_id.eq.{user['id']},participant2_id.eq.{participant2_id}),"
        f"and(participant1_id.eq.{participant2_id},participant2_id.eq.{user['id']})"
    ).execute()
    
    if existing.data:
        return existing.data[0]
    
    data = {
        "id": str(uuid.uuid4()),
        "participant1_id": user["id"],
        "participant2_id": participant2_id,
        "last_message": "",
        "last_message_at": datetime.utcnow().isoformat()
    }
    result = supabase.table("conversations").insert(data).execute()
    return result.data[0]

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, user=Depends(get_current_user)):
    conv = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    if not conv.data:
        raise HTTPException(404, "Conversation not found")
    if conv.data["participant1_id"] != user["id"] and conv.data["participant2_id"] != user["id"]:
        raise HTTPException(403, "Not part of conversation")
    
    messages = supabase.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").execute()
    return messages.data

@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, content: str, user=Depends(get_current_user)):
    conv = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    if not conv.data:
        raise HTTPException(404, "Conversation not found")
    if conv.data["participant1_id"] != user["id"] and conv.data["participant2_id"] != user["id"]:
        raise HTTPException(403, "Not part of conversation")
    
    data = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "content": content,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    result = supabase.table("messages").insert(data).execute()
    
    supabase.table("conversations").update({
        "last_message": content,
        "last_message_at": datetime.utcnow().isoformat()
    }).eq("id", conv_id).execute()
    
    return result.data[0]