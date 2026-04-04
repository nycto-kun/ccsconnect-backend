from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.models import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
from app.routes.auth import get_current_user
import uuid

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(user=Depends(get_current_user)):
    # Get conversations where user is participant1 or participant2
    convs1 = supabase.table("conversations").select("*").eq("participant1_id", user["id"]).execute()
    convs2 = supabase.table("conversations").select("*").eq("participant2_id", user["id"]).execute()
    conversations = convs1.data + convs2.data
    # Enrich with other user's name
    for conv in conversations:
        other_id = conv["participant2_id"] if conv["participant1_id"] == user["id"] else conv["participant1_id"]
        other = supabase.table("users").select("full_name").eq("id", other_id).single().execute()
        conv["other_user_name"] = other.data["full_name"] if other.data else "Unknown"
        conv["other_user_avatar"] = other.data["full_name"][0] if other.data else "U"
    return conversations

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(conv: ConversationCreate, user=Depends(get_current_user)):
    # Check if conversation already exists
    existing = supabase.table("conversations").select("*").or_(
        f"and(participant1_id.eq.{user['id']},participant2_id.eq.{conv.participant2_id}),"
        f"and(participant1_id.eq.{conv.participant2_id},participant2_id.eq.{user['id']})"
    ).execute()
    if existing.data:
        raise HTTPException(400, "Conversation already exists")
    data = {
        "id": str(uuid.uuid4()),
        "participant1_id": user["id"],
        "participant2_id": conv.participant2_id,
        "last_message": "",
        "last_message_at": "now()"
    }
    result = supabase.table("conversations").insert(data).execute()
    return result.data[0]

@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages(conv_id: str, user=Depends(get_current_user)):
    conv = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    if not conv.data:
        raise HTTPException(404, "Conversation not found")
    if conv.data["participant1_id"] != user["id"] and conv.data["participant2_id"] != user["id"]:
        raise HTTPException(403, "Not part of conversation")
    messages = supabase.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").execute()
    return messages.data

@router.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
async def send_message(conv_id: str, msg: MessageCreate, user=Depends(get_current_user)):
    conv = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    if not conv.data:
        raise HTTPException(404, "Conversation not found")
    if conv.data["participant1_id"] != user["id"] and conv.data["participant2_id"] != user["id"]:
        raise HTTPException(403, "Not part of conversation")
    data = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "content": msg.content,
        "is_read": False
    }
    result = supabase.table("messages").insert(data).execute()
    # Update conversation last message
    supabase.table("conversations").update({
        "last_message": msg.content,
        "last_message_at": "now()"
    }).eq("id", conv_id).execute()
    return result.data[0]

@router.put("/messages/{msg_id}/read")
async def mark_read(msg_id: str, user=Depends(get_current_user)):
    msg = supabase.table("messages").select("*").eq("id", msg_id).single().execute()
    if not msg.data:
        raise HTTPException(404, "Message not found")
    if msg.data["sender_id"] == user["id"]:
        raise HTTPException(400, "Cannot mark own message as read")
    supabase.table("messages").update({"is_read": True}).eq("id", msg_id).execute()
    return {"message": "Marked as read"}