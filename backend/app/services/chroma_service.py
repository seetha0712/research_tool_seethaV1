"""
ChromaDB service - DISABLED
Replaced with OpenAI embeddings + PostgreSQL pgvector
See embedding_service.py for the new implementation
"""
import logging
logger = logging.getLogger(__name__)

# ChromaDB is now disabled - we use OpenAI embeddings with pgvector instead
ENABLE_CHROMADB = False
client = None

def embed_and_store(chunks: list, article_id: int, user_id: int, model_name="all-MiniLM-L6-v2"):
    """Deprecated - ChromaDB disabled"""
    logger.debug(f"ChromaDB disabled - skipping storage for article {article_id}")
    return

def store_chunks(chunks, meta: dict):
    """Deprecated - ChromaDB disabled"""
    logger.debug("ChromaDB disabled - skipping chunk storage")
    return
