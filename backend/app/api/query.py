import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Query"])

# Dependency setup / singleton instance
query_service = QueryService()

@router.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    Executes a RAG query against cybersecurity frameworks, returning
    the synthesized answer alongside retrieved context and citations.
    """
    try:
        logger.info(f"Received API query Request: {request.question}, Frameworks: {request.frameworks}, Stream: {request.stream}")
        
        if request.stream:
            return StreamingResponse(
                query_service.process_query_stream(request.question, frameworks=request.frameworks),
                media_type="text/event-stream"
            )
            
        result = await query_service.process_query(request.question, frameworks=request.frameworks)
        
        return QueryResponse(
            answer=result["answer"],
            mapping_mode=result.get("mapping_mode", False),
            incident_mode=result.get("incident_mode", False),
            citations=result["citations"],
            frameworks_used=result.get("frameworks_used", []),
            retrieved_chunks=result["retrieved_chunks"]
        )
    except Exception as e:
        logger.error(f"Failed to process query on /query endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error executing query.")
