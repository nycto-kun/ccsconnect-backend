from sentence_transformers import SentenceTransformer
import numpy as np

# Lazy loading – model is not loaded until first use
_model = None

def get_model():
    """Load the sentence transformer model on first request."""
    global _model
    if _model is None:
        # Using a smaller model to reduce memory usage
        _model = SentenceTransformer('paraphrase-albert-small-v2')
    return _model

def vectorize_text(text: str) -> list:
    """
    Convert text into a vector embedding using the loaded model.
    """
    model = get_model()
    embedding = model.encode(text)
    return embedding.tolist()

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value between -1 and 1 (higher means more similar).
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))