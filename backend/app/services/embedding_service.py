import logging
import asyncio
import httpx
from typing import List, Union
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service responsible for interacting with the Jina Embeddings API.
    Converts text chunks into vector embeddings for semantic search.
    """
    
    def __init__(self):
        self.api_key = settings.jina_api_key
        self.url = "https://api.jina.ai/v1/embeddings"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        } if self.api_key else {}
        
    async def embed_text(self, text: Union[str, List[str]], retries: int = 3) -> Union[List[float], List[List[float]]]:
        """
        Call Jina API to generate vector embedding for the input text.
        Supports batching by taking a list of strings.
        Includes retries and exponential backoff for API errors.
        """
        if not self.api_key:
            logger.warning("Jina API key not found. Returning dummy embeddings.")
            if isinstance(text, str):
                return []
            return [[] for _ in text]

        inputs = [text] if isinstance(text, str) else text

        payload = {
            "model": "jina-embeddings-v2-base-en",
            "input": inputs
        }
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.url,
                        headers=self.headers,
                        json=payload,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract embeddings
                    embeddings = [item["embedding"] for item in data.get("data", [])]
                    
                    if isinstance(text, str):
                        return embeddings[0] if embeddings else []
                    return embeddings
                    
            except httpx.HTTPError as e:
                logger.error(f"Jina API error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Max retries reached. Embedding generation failed.")
                    raise e
                    
        return []
