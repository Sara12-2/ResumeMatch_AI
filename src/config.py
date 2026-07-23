"""Central configuration for ResumeMatch AI.

Score thresholds and TF-IDF parameters live here so matcher.py, the CLI,
and the web app all reference the same numbers.
"""

# TF-IDF vectorizer configuration used by src/matcher.py.
# Unigrams only: bigrams made the score too sensitive to exact phrasing
# (a resume and JD describing the same skills in different words scored
# much lower), which produced misleadingly low match scores. See README
# "How the matching actually works" for measurements behind this choice.
TFIDF_PARAMS = {
    "stop_words": "english",
    "ngram_range": (1, 1),
    "sublinear_tf": True,
    "lowercase": True,
}

# Match score (0-100) bands. Tuned against the synthetic pairs in
# tests/test_matcher.py and sample_data/ — see README "How the matching
# actually works" for the reasoning. Whole-document TF-IDF cosine
# similarity is lexical, so even a genuinely good resume/JD match rarely
# scores above ~50-60 - two independently-written documents don't share
# that much exact vocabulary even when the underlying skills line up.
SCORE_BAND_STRONG = 45
SCORE_BAND_MODERATE = 25


def score_band(score: float) -> str:
    if score >= SCORE_BAND_STRONG:
        return "Strong Match"
    if score >= SCORE_BAND_MODERATE:
        return "Moderate Match"
    return "Weak Match"
