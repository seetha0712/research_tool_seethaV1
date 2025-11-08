from PyPDF2 import PdfReader
import logging
logger = logging.getLogger(__name__)
def extract_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")

def chunk_text(text: str, max_tokens=800) -> list:
    """Split large text into overlapping chunks for embedding."""
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    words = text.split()
    chunks, chunk = [], []
    token_count = 0

    for word in words:
        tokens = len(encoding.encode(word + " "))
        if token_count + tokens > max_tokens:
            chunks.append(" ".join(chunk))
            chunk, token_count = [], 0
        chunk.append(word)
        token_count += tokens
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks