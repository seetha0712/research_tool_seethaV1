import chromadb
import logging
logger = logging.getLogger(__name__)

client = chromadb.PersistentClient(path="./chroma_db")  # Use persistent storage

def embed_and_store(chunks: list, article_id: int, user_id: int, model_name="all-MiniLM-L6-v2"):
    # Here, you would use e.g., SentenceTransformers or OpenAI embeddings to get vectors.
    # Let's say you have a function get_embedding(chunk) -> [float...]
    from sentence_transformers import SentenceTransformer
    import uuid 
    model = SentenceTransformer(model_name)
    vectors = model.encode(chunks).tolist()
    collection = client.get_or_create_collection("articles")

    # Generate unique ids for each chunk (could be based on article_id and chunk index)
    chunk_ids = [f"{article_id}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]


    for chunk, vec, chunk_id in zip(chunks, vectors, chunk_ids):
        collection.add(
            ids=[str(chunk_id)], 
            documents=[chunk],
            embeddings=[vec],
            metadatas=[{"article_id": article_id, "user_id": user_id}]
        )

def store_chunks(chunks, meta: dict):
    # meta: expects keys like article_id, user_id, etc.
    # Assume user_id is optional or comes from meta
    article_id = meta.get("article_id")
    user_id = meta.get("user_id", 0)  # or however you handle user
    embed_and_store(chunks, article_id=article_id, user_id=user_id)