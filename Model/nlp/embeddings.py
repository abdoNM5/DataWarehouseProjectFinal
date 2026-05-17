"""
Embedding module — encodes text into 384-dimensional vectors
using the paraphrase-multilingual-MiniLM-L12-v2 Sentence-Transformer.

Key concepts:
  - The model takes a sentence/paragraph → outputs a 384-d float vector
  - Similar texts → vectors point in the same direction → high cosine similarity
  - normalize_embeddings=True means cosine similarity = simple dot product (faster)
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Singleton model loading ──────────────────────────────────

_MODEL = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the model (singleton — loaded once, reused)."""
    global _MODEL
    if _MODEL is None:
        print("Loading SentenceTransformer model (first time, ~5 seconds)...")
        _MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("Model loaded!")
    return _MODEL


# ── Encoding functions ───────────────────────────────────────

def encode_text(text: str) -> np.ndarray:
    """
    Encode a single text into a 384-dimensional vector.
    The vector is L2-normalized, so cosine similarity = dot product.

    Args:
        text: any string (job description, candidate profile, etc.)

    Returns:
        np.ndarray of shape (384,) with float32 values
    """
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def encode_batch(texts: list, batch_size: int = 32) -> np.ndarray:
    """
    Encode multiple texts at once (much faster than one-by-one).

    Args:
        texts: list of N strings
        batch_size: how many texts to process at once (32 is good for CPU)

    Returns:
        np.ndarray of shape (N, 384)
    """
    model = _get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=True,
    )


# ── Serialization helpers (for JSONB storage in PostgreSQL) ──

def embedding_to_json(embedding: np.ndarray) -> str:
    """Convert a 384-d numpy array to a JSON string for JSONB storage."""
    return json.dumps(embedding.tolist())


def json_to_embedding(data) -> np.ndarray:
    """Convert a JSON string or list back to a numpy array.
    psycopg2 auto-deserializes JSONB columns into Python lists,
    so we handle both cases."""
    if isinstance(data, list):
        return np.array(data, dtype=np.float32)
    return np.array(json.loads(data), dtype=np.float32)
