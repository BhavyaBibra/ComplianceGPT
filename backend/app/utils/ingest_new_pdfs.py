import sys
import os
import asyncio
import logging

# Ensure backend directory is in the python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_dir)

from pathlib import Path
from app.services.ingestion_service import IngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Only ingest these new PDF folders
NEW_FRAMEWORKS = [
    ("cis", "cis/CIS_Controls__v8__Critical_Security_Controls__2023_08.pdf"),
    ("mitre", "mitre/getting-started-with-attack-october-2019.pdf"),
    ("nist-ai", "nist-ai/NIST.AI.100-1.pdf"),
]

async def main():
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, "data")
    ingestion_service = IngestionService(data_dir=data_dir)
    
    total = 0
    for framework, rel_path in NEW_FRAMEWORKS:
        pdf_path = Path(data_dir) / rel_path
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            continue
        logger.info(f"=== Ingesting [{framework}] {pdf_path.name} ===")
        count = await ingestion_service.ingest_file(pdf_path, framework)
        total += count
        logger.info(f"Stored {count} chunks for {pdf_path.name}")
    
    logger.info(f"========= DONE: {total} total new chunks ingested =========")

if __name__ == "__main__":
    asyncio.run(main())
