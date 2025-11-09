import chromadb
from chromadb.config import Settings
import os
import logging
logger = logging.getLogger(__name__)

# Make ChromaDB optional via environment variable
ENABLE_CHROMADB = os.getenv("ENABLE_CHROMADB", "false").lower() == "true"

if ENABLE_CHROMADB:
    try:
        # Disable telemetry to avoid PostHog connection errors
        client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info("ChromaDB enabled and initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        ENABLE_CHROMADB = False
        client = None
else:
    logger.info("ChromaDB disabled via environment variable")
    client = None

def embed_and_store(chunks: list, article_id: int, user_id: int, model_name="all-MiniLM-L6-v2"):
    """Store article chunks as embeddings in ChromaDB"""
    if not ENABLE_CHROMADB or client is None:
        logger.debug(f"Skipping ChromaDB storage for article {article_id} (disabled)")
        return

    try:
        from sentence_transformers import SentenceTransformer
        import uuid

        model = SentenceTransformer(model_name)
        vectors = model.encode(chunks).tolist()
        collection = client.get_or_create_collection("articles")

        # Generate unique ids for each chunk
        chunk_ids = [f"{article_id}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]

        for chunk, vec, chunk_id in zip(chunks, vectors, chunk_ids):
            collection.add(
                ids=[str(chunk_id)],
                documents=[chunk],
                embeddings=[vec],
                metadatas=[{"article_id": article_id, "user_id": user_id}]
            )
        logger.debug(f"Stored {len(chunks)} chunks for article {article_id}")
    except Exception as e:
        logger.warning(f"Failed to store embeddings for article {article_id}: {e}")

def store_chunks(chunks, meta: dict):
    """Store chunks with metadata"""
    if not ENABLE_CHROMADB:
        return

    article_id = meta.get("article_id")
    user_id = meta.get("user_id", 0)
    embed_and_store(chunks, article_id=article_id, user_id=user_id)