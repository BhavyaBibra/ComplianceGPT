from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import logging
from app.services.supabase_service import SupabaseService
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Conversations"])
supabase_service = SupabaseService()

# --- Schemas ---

class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    
class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str

class MessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[str]] = []
    evidence: Optional[List[Dict[str, Any]]] = []
    mapping_mode: bool = False
    incident_mode: bool = False

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    conversation_id: str
    created_at: str

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse]

# --- Dependencies ---

def get_user_id(authorization: str = Header(None)) -> str:
    """Extracts user ID from JWT token using Supabase Auth (public client)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
        
    token = authorization.split(" ")[1]
    
    try:
        user_response = supabase_service.client.auth.get_user(token)
        if hasattr(user_response, 'user') and user_response.user:
            return user_response.user.id
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# --- Endpoints ---
# READS use public client (RLS-enforced, scoped to user_id).
# WRITES use admin_client (service-role, bypasses RLS, user_id set explicitly).

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(user_id: str = Depends(get_user_id)):
    """Fetch all conversations for the authenticated user."""
    try:
        response = supabase_service.admin_client.table("conversations")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail="Database error retrieving conversations")

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreate, user_id: str = Depends(get_user_id)):
    """Create a new conversation for the user. Uses admin_client to bypass RLS."""
    try:
        data = {
            "user_id": user_id,
            "title": req.title
        }
        response = supabase_service.admin_client.table("conversations").insert(data).execute()
        
        if not response.data:
            raise Exception("Failed to insert conversation")
        
        logger.info(f"Conversation created: id={response.data[0]['id']}, user={user_id}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail="Database error creating conversation")

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, user_id: str = Depends(get_user_id)):
    """Fetch a specific conversation and all its associated messages."""
    try:
        # Get conversation metadata (admin_client filtered by user_id for ownership check)
        conv_response = supabase_service.admin_client.table("conversations")\
            .select("*")\
            .eq("id", conversation_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not conv_response.data:
            raise HTTPException(status_code=404, detail="Conversation not found or unauthorized")
            
        conv = conv_response.data[0]
        
        # Get all messages
        msg_response = supabase_service.admin_client.table("messages")\
            .select("*")\
            .eq("conversation_id", conversation_id)\
            .order("created_at", desc=False)\
            .execute()
            
        conv["messages"] = msg_response.data
        return conv
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error retrieving conversation")

@router.post("/conversations/{conversation_id}/message", response_model=MessageResponse)
async def append_message(conversation_id: str, req: MessageCreate, user_id: str = Depends(get_user_id)):
    """Append a message. Uses admin_client to bypass RLS."""
    try:
        # Verify ownership via admin_client
        conv_check = supabase_service.admin_client.table("conversations")\
            .select("id")\
            .eq("id", conversation_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not conv_check.data:
            raise HTTPException(status_code=403, detail="Unauthorized to modify this conversation")
            
        # Append message
        msg_data = req.dict()
        msg_data["conversation_id"] = conversation_id
        
        response = supabase_service.admin_client.table("messages").insert(msg_data).execute()
        
        if not response.data:
            raise Exception("Failed to insert message")
        
        logger.info(f"Message appended: conv={conversation_id}, role={req.role}")
            
        # Update conversation timestamp
        supabase_service.admin_client.table("conversations")\
            .update({"updated_at": datetime.utcnow().isoformat()})\
            .eq("id", conversation_id)\
            .execute()
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to append message to {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error appending message")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(get_user_id)):
    """Delete a conversation (messages auto cascade). Uses admin_client."""
    try:
        response = supabase_service.admin_client.table("conversations")\
            .delete()\
            .eq("id", conversation_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found or already deleted")
        
        logger.info(f"Conversation deleted: id={conversation_id}, user={user_id}")
        return {"status": "success", "deleted_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error deleting conversation")
