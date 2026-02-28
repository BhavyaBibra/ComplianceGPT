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
                    "similarity": item.get("similarity", 0.0),
                    "metadata": item.get("metadata", {}),
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
    Build structured context for the LLM with numbered chunks,
    framework labels, and similarity scores for reasoning clarity.
    
    Format:
        === Retrieved Context ===
        [Chunk 1 | Framework: CIS | Similarity: 0.83]
        <chunk text>
        
        [Chunk 2 | Framework: NIST80053 | Similarity: 0.79]
        <chunk text>
        === End Context ===
    """
    if not retrieval_results:
        return "=== Retrieved Context ===\nNo relevant documents found.\n=== End Context ==="
    
    context_parts = ["=== Retrieved Context ==="]
    
    for i, doc in enumerate(retrieval_results, 1):
        fw = doc.get("framework", "Unknown").upper()
        similarity = doc.get("similarity", 0.0)
        chunk = doc.get("chunk", "")
        metadata = doc.get("metadata", {})
        source_file = metadata.get("source_file", "") if isinstance(metadata, dict) else ""
        section_hint = metadata.get("section_hint", "") if isinstance(metadata, dict) else ""
        
        # Build header line
        header = f"[Chunk {i} | Framework: {fw} | Similarity: {similarity:.2f}"
        if source_file:
            header += f" | Source: {source_file}"
        if section_hint:
            header += f" | Section: {section_hint}"
        header += "]"
        
        context_parts.append(header)
        context_parts.append(chunk.strip())
        context_parts.append("")  # blank line separator
    
    context_parts.append("=== End Context ===")
    return "\n".join(context_parts)
