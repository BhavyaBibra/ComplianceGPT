import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import QueryService
from app.api.conversations import get_user_id, supabase_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Query"])

# Dependency setup / singleton instance
query_service = QueryService()

@router.post("/query")
async def query_endpoint(request: QueryRequest, user_id: str = Depends(get_user_id)):
    """
    Executes a RAG query against cybersecurity frameworks, returning
    the synthesized answer alongside retrieved context and citations.
    
    All persistence writes use admin_client (service-role) to bypass RLS.
    user_id is set explicitly to maintain ownership.
    """
    try:
        logger.info(f"Received API query Request: {request.question}, Stream: {request.stream}, Conv: {request.conversation_id}")
        
        admin = supabase_service.admin_client
        
        # 1. Resolve Conversation ID
        conv_id = request.conversation_id
        if not conv_id:
            title = request.question[:50] + "..." if len(request.question) > 50 else request.question
            conv_res = admin.table("conversations").insert({
                "user_id": user_id,
                "title": title
            }).execute()
            if conv_res.data:
                conv_id = conv_res.data[0]["id"]
                logger.info(f"New conversation created: id={conv_id}, user={user_id}")
            else:
                raise Exception("Failed to provision a new conversation timeline.")
                
        # 2. Save User Message
        admin.table("messages").insert({
            "conversation_id": conv_id,
            "role": "user",
            "content": request.question
        }).execute()
        logger.info(f"User message stored: conv={conv_id}")
        
        if request.stream:
            async def stream_and_save():
                # Ship new conversation_id to UI FIRST, before any RAG content
                if not request.conversation_id:
                    yield f"data: {json.dumps({'type': 'conversation_id', 'id': conv_id})}\n\n"
                
                full_answer = ""
                metadata = {}
                async for chunk in query_service.process_query_stream(request.question, frameworks=request.frameworks):
                    if chunk.startswith("data: "):
                        try:
                            data_str = chunk[6:].strip()
                            if data_str and data_str != "[DONE]":
                                parsed = json.loads(data_str)
                                if parsed["type"] == "metadata":
                                    metadata = parsed["data"]
                                elif parsed["type"] == "content":
                                    full_answer += parsed.get("text", "")
                        except Exception as e:
                            logger.error(f"Error parsing stream chunk for DB save: {e}")
                    yield chunk
                    
                # Save assistant message upon stream completion
                try:
                    admin.table("messages").insert({
                        "conversation_id": conv_id,
                        "role": "assistant",
                        "content": full_answer,
                        "citations": metadata.get("citations", []),
                        "evidence": metadata.get("retrieved_chunks", []),
                        "mapping_mode": metadata.get("mapping_mode", False),
                        "incident_mode": metadata.get("incident_mode", False)
                    }).execute()
                    logger.info(f"Assistant message stored: conv={conv_id}, length={len(full_answer)}")
                    
                    # Update conversation timestamp
                    admin.table("conversations").update({"updated_at": "now()"}).eq("id", conv_id).execute()
                except Exception as db_e:
                    logger.error(f"Failed to save assistant stream message: {db_e}")

            return StreamingResponse(
                stream_and_save(),
                media_type="text/event-stream"
            )
            
        result = await query_service.process_query(request.question, frameworks=request.frameworks)
        
        admin.table("messages").insert({
            "conversation_id": conv_id,
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"],
            "evidence": result["retrieved_chunks"],
            "mapping_mode": result.get("mapping_mode", False),
            "incident_mode": result.get("incident_mode", False)
        }).execute()
        logger.info(f"Assistant message stored (non-stream): conv={conv_id}")
        
        admin.table("conversations").update({"updated_at": "now()"}).eq("id", conv_id).execute()
        
        return QueryResponse(
            answer=result["answer"],
            mapping_mode=result.get("mapping_mode", False),
            incident_mode=result.get("incident_mode", False),
            citations=result["citations"],
            frameworks_used=result.get("frameworks_used", []),
            retrieved_chunks=result["retrieved_chunks"],
            conversation_id=conv_id
        )
    except Exception as e:
        logger.error(f"Failed to process query on /query endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error executing query.")
