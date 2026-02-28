import os
import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from app.services.embedding_service import EmbeddingService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Production ingestion pipeline for ComplianceGPT.
    
    Scans backend/data/<framework>/ folders, extracts text from PDFs,
    chunks intelligently, generates embeddings, and stores them in
    Supabase pgvector. Append-only by default.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.embedding_service = EmbeddingService()
        self.supabase_service = SupabaseService()

    # ── PDF Text Extraction ──────────────────────────────────────────────

    def _extract_pdf_text(self, file_path: Path) -> str:
        """
        Extract and clean text from all pages of a PDF.
        Removes page numbers, repeated headers, and normalizes whitespace.
        """
        if not PDF_SUPPORT:
            raise RuntimeError("PyPDF2 is not installed. Run: pip install PyPDF2")

        reader = PdfReader(str(file_path))
        pages_text = []

        for i, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            if not raw.strip():
                continue

            # Remove standalone page numbers (e.g. "  42  " or "Page 42")
            cleaned = re.sub(r'(?m)^\s*(?:Page\s*)?\d{1,4}\s*$', '', raw)
            # Collapse excessive whitespace
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = re.sub(r' {2,}', ' ', cleaned)

            pages_text.append(cleaned.strip())

        full_text = '\n\n'.join(pages_text)
        logger.info(f"  Extracted {len(reader.pages)} pages from {file_path.name} ({len(full_text)} chars)")
        return full_text

    # ── Intelligent Chunking ─────────────────────────────────────────────

    def _detect_section_heading(self, line: str) -> bool:
        """Heuristic: detect if a line is likely a section heading."""
        line = line.strip()
        if not line or len(line) > 120:
            return False
        # Numbered headings: "1.2 Title", "AC-2 Account Management"
        if re.match(r'^(\d+\.?\d*\.?\d*|[A-Z]{2,}-\d+)\s+[A-Z]', line):
            return True
        # ALL-CAPS headings
        if line.isupper() and len(line) > 3 and len(line) < 80:
            return True
        return False

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> List[Dict[str, str]]:
        """
        Intelligent chunking:
        1. Try to split at section headings for semantic boundaries.
        2. If sections are too large, subdivide with sliding window.
        3. Each chunk includes an optional section_hint for metadata.
        """
        lines = text.split('\n')
        sections: List[Dict[str, str]] = []  # {"heading": str, "text": str}
        current_heading = ""
        current_lines: List[str] = []

        for line in lines:
            if self._detect_section_heading(line) and current_lines:
                section_text = '\n'.join(current_lines).strip()
                if section_text:
                    sections.append({"heading": current_heading, "text": section_text})
                current_heading = line.strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        # Flush last section
        if current_lines:
            section_text = '\n'.join(current_lines).strip()
            if section_text:
                sections.append({"heading": current_heading, "text": section_text})

        # Now subdivide sections that are too large
        chunks: List[Dict[str, str]] = []
        for section in sections:
            text_block = section["text"]
            heading = section["heading"]

            if len(text_block) <= chunk_size * 1.2:
                # Small enough to keep as one chunk
                if text_block.strip():
                    chunks.append({"text": text_block, "section_hint": heading})
            else:
                # Sliding window subdivision
                sub_chunks = self._sliding_window_chunk(text_block, chunk_size, overlap)
                for sc in sub_chunks:
                    chunks.append({"text": sc, "section_hint": heading})

        # Safety: if we somehow got 0 chunks from a non-empty text, force at least one
        if not chunks and text.strip():
            chunks = [{"text": text[:chunk_size], "section_hint": ""}]

        return chunks

    def _sliding_window_chunk(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
        """Word-level sliding window chunking with overlap."""
        words = text.split()
        chunks = []
        current_chunk: List[str] = []
        current_len = 0

        for word in words:
            word_len = len(word) + 1
            if current_len + word_len > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))

                # Create overlap
                overlap_words = []
                overlap_len = 0
                for w in reversed(current_chunk):
                    if overlap_len + len(w) + 1 <= overlap:
                        overlap_words.insert(0, w)
                        overlap_len += len(w) + 1
                    else:
                        break

                current_chunk = overlap_words + [word]
                current_len = overlap_len + word_len
            else:
                current_chunk.append(word)
                current_len += word_len

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    # ── File Ingestion ───────────────────────────────────────────────────

    async def ingest_file(self, file_path: Path, framework: str) -> int:
        """
        Process a single PDF: extract → chunk → embed → store.
        Returns number of chunks successfully stored.
        """
        logger.info(f"  Processing: {file_path.name}")

        # 1. Extract text
        try:
            text = self._extract_pdf_text(file_path)
        except Exception as e:
            logger.error(f"  ✗ Failed to extract text from {file_path.name}: {e}")
            return 0

        if not text.strip():
            logger.warning(f"  ✗ No text extracted from {file_path.name}")
            return 0

        # 2. Chunk
        chunks = self._chunk_text(text, chunk_size=1000, overlap=150)
        logger.info(f"  Framework: {framework}, File: {file_path.name}, Total Chunks: {len(chunks)}")

        # 3. Embed + Store in batches
        inserted_count = 0
        batch_size = 10

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_texts = [c["text"] for c in batch]

            try:
                embeddings = await self.embedding_service.embed_text(batch_texts)

                for chunk_data, embedding in zip(batch, embeddings):
                    metadata = {
                        "source_file": file_path.name,
                        "section_hint": chunk_data.get("section_hint", ""),
                    }
                    await self.supabase_service.store_embedding_chunk(
                        chunk=chunk_data["text"],
                        embedding=embedding,
                        framework=framework,
                        metadata=metadata,
                    )
                    inserted_count += 1

            except Exception as e:
                logger.error(f"  ✗ Batch {i // batch_size + 1} failed for {file_path.name}: {e}")

        logger.info(f"  ✓ Inserted {inserted_count} rows for {framework}/{file_path.name}")
        return inserted_count

    # ── Full Corpus Ingestion ────────────────────────────────────────────

    async def ingest_all_frameworks(self) -> Dict[str, int]:
        """
        Scan all framework folders under data_dir and ingest every PDF.
        Returns dict of { framework: chunk_count }.
        """
        logger.info(f"═══ Starting full corpus ingestion from {self.data_dir} ═══")
        results: Dict[str, int] = {}

        if not self.data_dir.exists() or not self.data_dir.is_dir():
            logger.error(f"Data directory does not exist: {self.data_dir}")
            return results

        for entry in sorted(os.scandir(self.data_dir), key=lambda e: e.name):
            if not entry.is_dir():
                continue

            framework = entry.name
            framework_path = Path(entry.path)
            pdf_files = list(framework_path.rglob("*.pdf"))

            if not pdf_files:
                logger.warning(f"  ⚠ No PDF files in {framework}/, skipping")
                continue

            logger.info(f"\n── Framework: {framework} ({len(pdf_files)} PDF{'s' if len(pdf_files) > 1 else ''}) ──")
            framework_total = 0

            for pdf_path in pdf_files:
                count = await self.ingest_file(pdf_path, framework)
                framework_total += count

            results[framework] = framework_total
            logger.info(f"  ═ {framework} total: {framework_total} chunks\n")

        logger.info("═══ Ingestion complete ═══")
        for fw, count in results.items():
            logger.info(f"  {fw}: {count} chunks")
        logger.info(f"  TOTAL: {sum(results.values())} chunks across {len(results)} frameworks")

        return results

    # ── Reset (clear embeddings table) ───────────────────────────────────

    async def reset_embeddings(self):
        """Delete all rows from the embeddings table. Use with caution."""
        if not self.supabase_service.admin_client:
            logger.error("Cannot reset: admin client not configured")
            return
        try:
            # Use a filter that matches all rows (created_at is always set)
            self.supabase_service.admin_client.table("embeddings").delete().gte("created_at", "2000-01-01").execute()
            logger.info("✓ Embeddings table cleared")
        except Exception as e:
            logger.error(f"✗ Failed to clear embeddings: {e}")
