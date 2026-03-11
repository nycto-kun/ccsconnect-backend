from sentence_transformers import SentenceTransformer
import numpy as np

# Load the model once at startup
model = SentenceTransformer('all-MiniLM-L6-v2')

def vectorize_text(text: str) -> list:
    """
    Convert text into a 384‑dimensional vector.
    """
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