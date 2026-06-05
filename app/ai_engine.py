from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('paraphrase-albert-small-v2')
    return _model

def vectorize_text(text: str) -> list:
    model = get_model()
    embedding = model.encode(text)
    return embedding.tolist()

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))