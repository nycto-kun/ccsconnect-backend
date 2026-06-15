import numpy as np
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CHANGE THIS - Use 384 dimensions to match database
EMBEDDING_DIM = 384  # Changed from 64 to 384

# Common skill keywords for better matching
SKILL_KEYWORDS = {
    'python': ['python', 'django', 'flask', 'fastapi', 'numpy', 'pandas'],
    'javascript': ['javascript', 'react', 'vue', 'angular', 'node', 'express'],
    'java': ['java', 'spring', 'maven', 'gradle'],
    'sql': ['sql', 'postgresql', 'mysql', 'database', 'query'],
    'communication': ['communication', 'teamwork', 'leadership', 'presentation'],
    'git': ['git', 'github', 'version control'],
    'docker': ['docker', 'container', 'kubernetes'],
    'aws': ['aws', 'cloud', 'ec2', 's3'],
    'html': ['html', 'css', 'frontend', 'web'],
    'problem_solving': ['problem solving', 'analytical', 'debugging', 'troubleshooting'],
}

def get_skill_category(text: str) -> str:
    """Categorize text into a skill category"""
    text_lower = text.lower()
    for category, keywords in SKILL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    return 'general'

def vectorize_text(text: str) -> list:
    """
    Convert text into a vector embedding using a lightweight hash-based method.
    Generates 384-dimensional vectors to match database schema.
    """
    if not text or text.strip() == "":
        return [0.0] * EMBEDDING_DIM
    
    text_lower = text.lower()
    embedding = [0.0] * EMBEDDING_DIM
    
    # Split into words and phrases
    words = text_lower.split()
    
    # Add word-based features
    for word in words[:300]:  # Limit words for performance
        # Create a hash for the word
        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
        for i in range(5):  # Spread across 5 dimensions
            idx = (hash_val + i) % EMBEDDING_DIM
            embedding[idx] += 1.0
    
    # Add skill category features
    category = get_skill_category(text)
    category_hash = int(hashlib.md5(category.encode()).hexdigest(), 16)
    idx = category_hash % EMBEDDING_DIM
    embedding[idx] += 10.0  # Boost for category match
    
    # Add bonus for detected skills
    for category, keywords in SKILL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                category_hash = int(hashlib.md5(category.encode()).hexdigest(), 16)
                idx = category_hash % EMBEDDING_DIM
                embedding[idx] += 5.0
    
    # Normalize the embedding
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = [v / norm for v in embedding]
    
    logger.info(f"Generated {EMBEDDING_DIM}-dim embedding for text length {len(text)}")
    return embedding

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two vectors"""
    try:
        a = np.array(vec_a)
        b = np.array(vec_b)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        return 0.0

def extract_skills_from_text(text: str) -> list:
    """Extract skills from text using keyword matching"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = []
    
    for category, keywords in SKILL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_skills.append(category.capitalize())
                break
    
    return list(set(found_skills))