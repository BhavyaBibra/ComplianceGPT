import logging
from typing import List, Dict, Any
from app.services.embedding_service import EmbeddingService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class RetrievalService:
    """
    Retrieval service using Jina embeddings and pgvector semantic search
    to match RAG user questions to chunks.
    """
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.supabase_service = SupabaseService()
        
    async def get_relevant_chunks(self, query: str, frameworks: List[str] | None = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Accept query text, generate embedding, and retrieve top-k chunks from Supabase.
        """
        try:
            logger.info(f"Generating embedding for query...")
            query_embedding = await self.embedding_service.embed_text(query)
            
            if not query_embedding:
                logger.warning("Query embedding empty. Returning no chunks.")
                return []
                
            # We fetch more chunks initially to allow for filtering
            fetch_limit = limit * 3 if frameworks else limit
            logger.info(f"Retrieving top {fetch_limit} chunks from vector DB...")
            results = await self.supabase_service.fetch_documents(query_embedding, limit=fetch_limit)
            
            structured_results = []
            for item in (results or []):
                chunk_struct = {
                    "chunk": item.get("chunk", ""),
                    "framework": item.get("framework", "Unknown"),
                    "similarity": item.get("similarity", 0.0)
                }
                
                # Apply framework filtering natively
                if frameworks and chunk_struct["framework"] not in frameworks:
                    continue
                    
                structured_results.append(chunk_struct)
                if len(structured_results) >= limit:
                    break
                
            return structured_results
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

def build_context(retrieval_results: List[Dict[str, Any]]) -> str:
    """
    Concatenate chunks and group by framework labels to build LLM context string.
    Example:
    === NIST80053 ===
    chunks...
    """
    # Group results by framework
    grouped: Dict[str, List[str]] = {}
    for doc in retrieval_results:
        fw = doc.get("framework", "Unknown")
        chunk = doc.get("chunk", "")
        if fw not in grouped:
            grouped[fw] = []
        grouped[fw].append(chunk)
        
    context_parts = []
    for fw, chunks in grouped.items():
        context_parts.append(f"=== {fw.upper()} ===")
        context_parts.append("\n\n".join(chunks))
        
    return "\n\n".join(context_parts)
