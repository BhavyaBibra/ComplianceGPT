import logging
from typing import List, Dict, Any
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Service responsible for interacting with Supabase.
    Handles authentication, data retrieval, and pgvector operations.
    """
    
    def __init__(self):
        if settings.supabase_url and settings.supabase_anon_key:
            self.client: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
        else:
            self.client = None
            logger.warning("Supabase credentials missing. SupabaseService in dummy mode.")
            
    async def store_embedding_chunk(self, chunk: str, embedding: List[float], framework: str, metadata: Dict[str, Any]):
        """
        Inserts a document chunk and its embedding into the Supabase pgvector table.
        """
        if not self.client:
            logger.info("Dummy insert (Supabase unconfigured): chunk=%s..., framework=%s", chunk[:30], framework)
            return
            
        try:
            # Assumes an 'embeddings' table with text/vector/metadata fields
            data = {
                "chunk": chunk,
                "embedding": embedding,
                "framework": framework,
                "metadata": metadata
            }
            response = self.client.table("embeddings").insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to store embedding chunk in Supabase: {e}")
            raise e
        
    async def fetch_documents(self, query_embedding: list[float], limit: int = 5):
        """
        Search pgvector database for relevant compliance documents using match_embeddings RPC.
        """
        if not self.client:
            logger.info("Dummy search: Returning empty results (Supabase unconfigured).")
            return []
            
        try:
            response = self.client.rpc(
                "match_embeddings", 
                {"query_embedding": query_embedding, "match_threshold": 0.5, "match_count": limit}
            ).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching documents from Supabase: {e}")
            return []
        
    async def verify_user_session(self, token: str):
        """
        Placeholder method: Validate user auth token with Supabase Auth.
        """
        pass
