import os
import logging
from typing import List
from pathlib import Path
from app.services.embedding_service import EmbeddingService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Service responsible for loading text files, chunking data, 
    generating embeddings, and storing them in Supabase pgvector.
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.embedding_service = EmbeddingService()
        self.supabase_service = SupabaseService()
        
    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """
        Splits text semantically based on words, with a target size and overlap.
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_len = 0
        
        for word in words:
            word_len = len(word) + 1  # include space character
            
            if current_len + word_len > chunk_size and current_chunk:
                # Compile chunk
                chunks.append(" ".join(current_chunk))
                
                # Create overlap of the last N words
                overlap_words = []
                overlap_len = 0
                for w in reversed(current_chunk):
                    if overlap_len + len(w) + 1 <= overlap:
                        overlap_words.insert(0, w)
                        overlap_len += len(w) + 1
                    else:
                        break
                
                # Start new chunk with overlap + new word
                current_chunk = overlap_words + [word]
                current_len = overlap_len + word_len
            else:
                current_chunk.append(word)
                current_len += word_len
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    async def ingest_file(self, file_path: Path, framework: str) -> int:
        """
        Reads a file, chunks the text, creates embeddings, and stores them in Supabase.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return 0
            
        chunks = self._chunk_text(content, chunk_size=800, overlap=100)
        stored_count = 0
        batch_size = 10  # Process in small batches
        
        logger.info(f"Chunked {file_path.name} into {len(chunks)} chunks.")
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            try:
                # 1. Generate embeddings using Jina via EmbeddingService
                embeddings = await self.embedding_service.embed_text(batch_chunks)
                
                # 2. Store chunks + embeddings in Supabase
                for chunk, embedding in zip(batch_chunks, embeddings):
                    metadata = {"filename": file_path.name}
                    await self.supabase_service.store_embedding_chunk(
                        chunk, embedding, framework, metadata
                    )
                    stored_count += 1
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size} for {file_path.name}: {e}")
                
        return stored_count

    async def ingest_all_frameworks(self) -> int:
        """
        Recursively scans data_dir, loads .txt and .md files, and orchestrates the ingestion pipeline.
        The framework name is inferred from the parent folder (e.g. data/nist80053/).
        """
        logger.info(f"Starting document ingestion pipeline from {self.data_dir}")
        target_exts = {".txt", ".md"}
        total_stored = 0
        
        if not self.data_dir.exists() or not self.data_dir.is_dir():
            logger.error(f"Data directory {self.data_dir} does not exist.")
            return 0
            
        for entry in os.scandir(self.data_dir):
            if entry.is_dir():
                framework_name = entry.name
                logger.info(f"-- Scanning framework: {framework_name} --")
                
                for file_path in Path(entry.path).rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in target_exts:
                        logger.info(f"Ingesting {file_path.name}...")
                        chunks_processed = await self.ingest_file(file_path, framework_name)
                        total_stored += chunks_processed
                        logger.info(f"Stored {chunks_processed} chunks for {file_path.name}")
                        
        logger.info(f"Ingestion pipeline complete. Stored a total of {total_stored} chunks.")
        return total_stored
