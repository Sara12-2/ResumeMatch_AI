"""Deterministic resume-vs-job-description similarity scoring.

Classical NLP only: scikit-learn's TfidfVectorizer + cosine similarity.
No LLM calls, no network access - runs fully offline. See src/config.py
for the exact vectorizer settings and score-band thresholds.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import TFIDF_PARAMS, score_band


class EmptyDocumentError(ValueError):
    pass


def compute_match_score(resume_text: str, jd_text: str) -> dict:
    """Score how well resume_text matches jd_text.

    Fits a TF-IDF vectorizer on the two-document corpus [resume, jd] and
    takes the cosine similarity between the resulting vectors.

    Returns:
        {"score": float 0-100, "band": "Strong Match"/"Moderate Match"/"Weak Match"}
    """
    if not resume_text or not resume_text.strip():
        raise EmptyDocumentError("resume_text must not be empty")
    if not jd_text or not jd_text.strip():
        raise EmptyDocumentError("jd_text must not be empty")

    vectorizer = TfidfVectorizer(**TFIDF_PARAMS)
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
    score = round(float(similarity) * 100, 2)

    return {
        "score": score,
        "band": score_band(score),
    }
