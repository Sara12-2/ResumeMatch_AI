import pytest

from src.config import score_band
from src.matcher import EmptyDocumentError, compute_match_score

IDENTICAL_TEXT = (
    "Backend engineer with experience in Python, Flask, PostgreSQL, Docker, "
    "and REST API design. Strong background in automated testing with pytest."
)

UNRELATED_TEXT = (
    "Grandmother's chocolate cake recipe requires flour, sugar, butter, eggs, "
    "vanilla extract, and a warm oven for forty five minutes before cooling."
)


def test_identical_documents_score_100():
    result = compute_match_score(IDENTICAL_TEXT, IDENTICAL_TEXT)
    assert result["score"] == 100.0
    assert result["band"] == "Strong Match"


def test_completely_unrelated_documents_score_zero():
    resume = (
        "Python Flask Django PostgreSQL REST API Docker AWS pytest backend "
        "engineer software development"
    )
    result = compute_match_score(resume, UNRELATED_TEXT)
    assert result["score"] == 0.0
    assert result["band"] == "Weak Match"


def test_high_skill_overlap_resume_scores_strong():
    # Shares nearly all key terms (Python, Flask, REST APIs, PostgreSQL,
    # Docker, pytest, AWS EC2/S3, Redis), just phrased slightly differently.
    resume = (
        "Backend engineer experienced in Python, Flask, REST APIs, PostgreSQL, "
        "Docker, and pytest. Deployed services on AWS EC2 and S3, added Redis "
        "caching for performance."
    )
    jd = (
        "Looking for a backend engineer skilled in Python and Flask to build "
        "REST APIs. Must know PostgreSQL, Docker, pytest, and AWS EC2 and S3. "
        "Redis experience is a plus."
    )
    result = compute_match_score(resume, jd)
    assert 45 <= result["score"] <= 65
    assert result["band"] == "Strong Match"


def test_partial_skill_overlap_resume_scores_moderate():
    # Shares the core tools (SQL, Python, Excel, Tableau) but each document
    # also has its own unique vocabulary (PowerBI, forecasting, dashboards),
    # landing in between - a "Moderate", not "Strong", match.
    resume = (
        "Data analyst with experience in SQL, Excel, Python pandas, and "
        "Tableau dashboards for business reporting."
    )
    jd = (
        "Looking for a data analyst skilled in SQL and Python, experience "
        "with Tableau or PowerBI, and strong Excel skills for financial "
        "reporting and forecasting models."
    )
    result = compute_match_score(resume, jd)
    assert 25 <= result["score"] < 45
    assert result["band"] == "Moderate Match"


def test_low_overlap_resume_scores_weak():
    resume = "Frontend developer skilled in React, TypeScript, CSS, and Figma design handoff."
    jd = "Looking for a backend engineer skilled in Python, Django, PostgreSQL, and Kubernetes."
    result = compute_match_score(resume, jd)
    assert result["score"] < 25
    assert result["band"] == "Weak Match"


def test_empty_resume_raises():
    with pytest.raises(EmptyDocumentError):
        compute_match_score("", "some jd text")


def test_empty_jd_raises():
    with pytest.raises(EmptyDocumentError):
        compute_match_score("some resume text", "   ")


def test_score_band_thresholds():
    assert score_band(45) == "Strong Match"
    assert score_band(44.99) == "Moderate Match"
    assert score_band(25) == "Moderate Match"
    assert score_band(24.99) == "Weak Match"
