import asyncio
import logging
import sys
import os

# Add the backend directory to sys.path to allow importing from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.ERROR) # suppress verbose http logs for cleaner output

async def main():
    print("Starting embedding dimension diagnostic...\n")
    
    service = EmbeddingService()
    test_text = "dimension test"
    
    print(f"Generating embedding for text: '{test_text}'")
    
    embedding = await service.embed_text(test_text)
    
    if not embedding:
        print("ERROR: Failed to generate embedding. Check API keys and network connection.")
        return
        
    dim = len(embedding)
    print(f"Embedding dimension: {dim}")
    print(f"Sample values (first 5): {embedding[:5]}\n")
    
    print("--- Diagnostic Check ---")
    print(f"1. Generated Embedding Dimension: {dim}")
    print("2. Compare this to your Supabase pgvector column and match_embeddings RPC function.")
    print("3. Check the Supabase SQL Editor: ")
    print("   SELECT probin FROM pg_attribute WHERE attrelid = 'embeddings'::regclass AND attname = 'embedding';")
    print("   Or simply look at the table schema definition (e.g., vector(1024) vs vector(768)).")
    print(f"\nWARNING: If the DB column dimension != {dim}, the match_embeddings RPC will fail or return an error.")
    print("To fix: Recreate the 'embeddings' table column and the 'match_embeddings' RPC to use vector({}).".format(dim))

if __name__ == "__main__":
    asyncio.run(main())
