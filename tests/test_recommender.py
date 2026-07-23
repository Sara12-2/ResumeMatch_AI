import pytest

from src import recommender

SAMPLE_REPORT = {
    "overall_score": 50.0,
    "overall_band": "Moderate Match",
    "skill_coverage_pct": 50.0,
    "matched_skills": ["Python"],
    "missing_skills": ["Docker"],
    "extra_skills": [],
}


def test_generate_suggestions_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(recommender, "_client", None)

    with pytest.raises(recommender.RecommenderError):
        recommender.generate_suggestions(SAMPLE_REPORT)


def test_missing_api_key_error_message_is_actionable(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(recommender, "_client", None)

    with pytest.raises(recommender.RecommenderError, match="GROQ_API_KEY"):
        recommender.generate_suggestions(SAMPLE_REPORT)
