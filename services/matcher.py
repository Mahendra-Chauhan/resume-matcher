"""
matcher.py — the core matching engine.
Turns text into embeddings (numeric vectors), compares them, and scores resumes.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

# Loaded ONCE when the app starts — reused for every request (fast).
_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding(text):
    """Converts text into a 384-number vector representing its meaning."""
    if not text:
        text = ""
    vector = _model.encode(text)
    return vector.astype(np.float32)


def embedding_to_bytes(vector):
    """Converts a numpy vector to bytes, for storing in the database."""
    return vector.tobytes()


def bytes_to_embedding(blob):
    """Converts bytes back into a numpy vector, for reading from the database."""
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(vec_a, vec_b):
    """
    Measures how similar two vectors are, from -1 (opposite) to 1 (identical).
    We convert this to a 0-100 score for display.
    """
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def semantic_search(query_text, candidates, top_k=5):
    """
    Finds the candidates whose resume text is most similar in MEANING to the
    query — not keyword matching. Used as the chatbot's fallback for
    open-ended questions that don't hit an exact skill/score pattern.

    candidates: list of dicts, each must have an "embedding_vec" (numpy array).
    Returns the top_k candidates, sorted by similarity (best first).
    """
    query_vec = get_embedding(query_text)
    scored = []
    for c in candidates:
        vec = c.get("embedding_vec")
        if vec is None:
            continue
        sim = cosine_similarity(query_vec, vec)
        scored.append((sim, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def compute_match_score(resume_text, resume_skills, jd_text, jd_skills, jd_min_exp, resume_exp):
    """
    Combines semantic similarity with skill overlap into one final score (0-100).
    """
    resume_vec = get_embedding(resume_text)
    jd_vec = get_embedding(jd_text)
    semantic_sim = cosine_similarity(resume_vec, jd_vec)  # -1 to 1
    semantic_score = (semantic_sim + 1) / 2 * 100  # normalize to 0-100

    # Skill overlap: what % of required skills does this resume have?
    jd_skills_set = set(s.lower() for s in jd_skills)
    resume_skills_set = set(s.lower() for s in resume_skills)
    if jd_skills_set:
        overlap = len(jd_skills_set & resume_skills_set) / len(jd_skills_set)
    else:
        overlap = 0.5  # neutral if JD had no clear skills extracted
    skill_score = overlap * 100

    # Experience match: does resume meet the JD's minimum?
    if jd_min_exp is None or resume_exp is None:
        exp_score = 50  # neutral if unknown
    elif resume_exp >= jd_min_exp:
        exp_score = 100
    else:
        exp_score = max(0, (resume_exp / jd_min_exp) * 100)

    final_score = (0.6 * semantic_score) + (0.25 * skill_score) + (0.15 * exp_score)

    matched = sorted(jd_skills_set & resume_skills_set)
    missing = sorted(jd_skills_set - resume_skills_set)

    return round(final_score, 1), matched, missing, resume_vec