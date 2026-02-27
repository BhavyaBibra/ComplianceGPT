import logging
from typing import List, Dict, Any
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Service responsible for interacting with Supabase.
    
    Two clients are maintained:
      - client (anon key): Used for auth verification and read operations.
        Respects Row Level Security (RLS) policies.
      - admin_client (service role key): Used for persistence writes 
        (conversations, messages). Bypasses RLS but explicitly sets user_id
        to maintain logical ownership. NEVER expose this key to the frontend.
    """
    
    def __init__(self):
        # --- Public / Anon Client (RLS-enforced) ---
        if settings.supabase_url and settings.supabase_anon_key:
            self.client: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
            logger.info("Supabase public client initialized.")
        else:
            self.client = None
            logger.warning("Supabase credentials missing. Public client in dummy mode.")
        
        # --- Admin / Service Role Client (bypasses RLS) ---
        if settings.supabase_url and settings.supabase_service_role_key:
            self.admin_client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
            logger.info("Supabase admin (service-role) client initialized.")
        else:
            self.admin_client = None
            logger.warning("SUPABASE_SERVICE_ROLE_KEY missing. Admin client unavailable — persistence writes will fail.")
            
    async def store_embedding_chunk(self, chunk: str, embedding: List[float], framework: str, metadata: Dict[str, Any]):
        """
        Inserts a document chunk and its embedding into the Supabase pgvector table.
        Uses admin_client to bypass RLS on the embeddings table.
        """
        if not self.admin_client:
            logger.info("Dummy insert (admin client unconfigured): chunk=%s..., framework=%s", chunk[:30], framework)
            return
            
        try:
            data = {
                "chunk": chunk,
                "embedding": embedding,
                "framework": framework,
                "metadata": metadata
            }
            response = self.admin_client.table("embeddings").insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to store embedding chunk in Supabase: {e}")
            raise e
        
    async def fetch_documents(self, query_embedding: list[float], limit: int = 5):
        """
        Search pgvector database for relevant compliance documents using match_embeddings RPC.
        Uses public client (read operations are safe with RLS).
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
