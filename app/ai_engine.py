from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    """Load the sentence transformer model once and cache it"""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def vectorize_text(text: str) -> list:
    """Convert text into a vector embedding"""
    if not text or text.strip() == "":
        return [0.0] * 384
    
    model = get_model()
    if len(text) > 5000:
        text = text[:5000]
    embedding = model.encode(text)
    return embedding.tolist()

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two vectors"""
    a = np.array(vec_a)
    b = np.array(vec_b)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))