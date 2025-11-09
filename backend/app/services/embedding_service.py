"""
OpenAI Embedding Service for vector search
Replaces sentence-transformers/ChromaDB with OpenAI embeddings + pgvector
"""
import os
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions, cost-effective
EMBEDDING_ENABLED = os.getenv("ENABLE_EMBEDDINGS", "true").lower() == "true"


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate OpenAI embedding for the given text.
    Returns a list of floats (vector) or None if disabled/failed.
    """
    if not EMBEDDING_ENABLED:
        logger.info("Embeddings disabled via ENABLE_EMBEDDINGS")
        return None

    if not client:
        logger.warning("OpenAI client not initialized - missing OPENAI_API_KEY")
        return None

    if not text or not text.strip():
        logger.warning("Empty text provided for embedding")
        return None

    try:
        # Truncate text to avoid token limits (8191 tokens max)
        # Roughly 4 chars per token, so limit to ~30k chars
        truncated_text = text[:30000]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=truncated_text
        )

        embedding = response.data[0].embedding
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts (up to 2048 texts per batch).
    Returns a list of embeddings (or None for failures).
    """
    if not EMBEDDING_ENABLED or not client:
        return [None] * len(texts)

    if not texts:
        return []

    try:
        # Truncate each text
        truncated_texts = [t[:30000] for t in texts if t and t.strip()]

        if not truncated_texts:
            return [None] * len(texts)

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=truncated_texts
        )

        embeddings = [data.embedding for data in response.data]
        logger.info(f"Generated {len(embeddings)} embeddings in batch")
        return embeddings

    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return [None] * len(texts)
