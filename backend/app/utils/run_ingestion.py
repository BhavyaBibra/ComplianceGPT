#!/usr/bin/env python3
"""
ComplianceGPT Ingestion CLI

Usage:
    python -m app.utils.run_ingestion                # Append mode (default)
    python -m app.utils.run_ingestion --reset         # Clear table first, then ingest
    python -m app.utils.run_ingestion --verify-only   # Just print current counts
"""
import sys
import os
import asyncio
import argparse
import logging

# Ensure backend directory is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_dir)

from app.services.ingestion_service import IngestionService
from app.services.supabase_service import SupabaseService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def verify_counts():
    """Query embeddings table and print per-framework counts."""
    svc = SupabaseService()
    client = svc.admin_client or svc.client
    if not client:
        logger.error("No Supabase client available for verification.")
        return

    logger.info("\n═══ Verification: Embeddings per Framework ═══")
    try:
        # Fetch all frameworks
        res = client.table("embeddings").select("framework").execute()
        rows = res.data or []

        counts: dict[str, int] = {}
        for row in rows:
            fw = row.get("framework", "unknown")
            counts[fw] = counts.get(fw, 0) + 1

        if not counts:
            logger.info("  (empty — no embeddings found)")
        else:
            for fw in sorted(counts.keys()):
                logger.info(f"  {fw}: {counts[fw]} chunks")
            logger.info(f"  ─────────────────────")
            logger.info(f"  TOTAL: {sum(counts.values())} chunks")

    except Exception as e:
        logger.error(f"Verification query failed: {e}")


async def main():
    parser = argparse.ArgumentParser(description="ComplianceGPT Ingestion CLI")
    parser.add_argument("--reset", action="store_true",
                        help="Clear all embeddings before ingesting. USE WITH CAUTION.")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only print current framework counts, do not ingest.")
    args = parser.parse_args()

    # Resolve data directory: backend/../data == project_root/data
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, "data")

    if args.verify_only:
        await verify_counts()
        return

    ingestion_service = IngestionService(data_dir=data_dir)

    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Mode: {'RESET + INGEST' if args.reset else 'APPEND (safe)'}")

    if args.reset:
        logger.warning("⚠ --reset flag detected. Clearing embeddings table...")
        await ingestion_service.reset_embeddings()

    # Run full ingestion
    results = await ingestion_service.ingest_all_frameworks()

    # Print summary
    logger.info("\n═══════════════════════════════════════════")
    logger.info("  INGESTION COMPLETE")
    logger.info("═══════════════════════════════════════════")
    for fw, count in results.items():
        logger.info(f"  {fw}: {count} chunks")
    logger.info(f"  TOTAL: {sum(results.values())} chunks")
    logger.info("═══════════════════════════════════════════")

    # Auto-verify
    await verify_counts()


if __name__ == "__main__":
    asyncio.run(main())
