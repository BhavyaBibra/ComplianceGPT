import sys
import os
import asyncio
import logging

# Ensure backend directory is in the python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_dir)

from app.services.ingestion_service import IngestionService

# Configure simple structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Ingestion CLI...")
    
    # Path to the data directory located in the project root
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, "data")
    
    # Instantiate the ingestion service with the data folder
    ingestion_service = IngestionService(data_dir=data_dir)
    
    logger.info(f"Resolved data directory: {data_dir}")
    
    # Run the ingestion script
    total_chunks = await ingestion_service.ingest_all_frameworks()
    
    logger.info("=========================================")
    logger.info(f"SUCCESS: Ingestion process finished.")
    logger.info(f"Total chunks processed: {total_chunks}")
    logger.info("=========================================")
    
if __name__ == "__main__":
    asyncio.run(main())
