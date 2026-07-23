from src.matcher import section_contributions
from src.parser import split_into_sections
from src.skill_extractor import analyze_skill_gap, extract_skills

RESUME_TEXT = (
    "Experience with Python, Flask, PostgreSQL, Docker, pytest, and Redis. "
    "Also skilled in React for frontend work."
)
JD_TEXT = (
    "Looking for a Python and Django developer with PostgreSQL, Docker, "
    "Kubernetes, and AWS experience."
)


def test_extract_skills_finds_known_terms():
    skills = extract_skills(RESUME_TEXT)
    assert {"Python", "Flask", "PostgreSQL", "Docker", "pytest", "Redis", "React"} <= skills


def test_extract_skills_matches_aliases_case_insensitively():
    skills = extract_skills("Worked with POSTGRES, kubernetes (k8s), and JS daily.")
    assert "PostgreSQL" in skills
    assert "Kubernetes" in skills
    assert "JavaScript" in skills


def test_extract_skills_no_taxonomy_terms_returns_empty_set():
    skills = extract_skills("We are seeking a wonderful human being to join our happy team.")
    assert skills == set()


def test_analyze_skill_gap_matched_missing_extra():
    result = analyze_skill_gap(RESUME_TEXT, JD_TEXT)

    assert result["matched_skills"] == ["Docker", "PostgreSQL", "Python"]
    assert result["missing_skills"] == ["AWS", "Django", "Kubernetes"]
    assert result["extra_skills"] == ["Flask", "React", "Redis", "pytest"]
    assert result["skill_coverage_pct"] == 50.0


def test_analyze_skill_gap_zero_jd_skills_gives_zero_coverage():
    result = analyze_skill_gap(RESUME_TEXT, "We just need a great culture fit for our team.")
    assert result["missing_skills"] == []
    assert result["skill_coverage_pct"] == 0.0


def test_section_contributions_ranks_relevant_section_highest():
    resume = (
        "Summary\n"
        "Backend developer with a few years of experience.\n"
        "Skills\n"
        "Python, Flask, PostgreSQL, Docker, pytest, AWS EC2, S3, Redis.\n"
        "Education\n"
        "B.S. in underwater basket weaving from a small college.\n"
    )
    jd = (
        "Looking for a backend engineer skilled in Python, Flask, "
        "PostgreSQL, Docker, pytest, AWS, and Redis."
    )
    sections = split_into_sections(resume)
    ranked = section_contributions(sections, jd)

    assert ranked[0]["section"] == "Skills"
    assert ranked[-1]["section"] == "Education"
    assert ranked[0]["score"] > ranked[-1]["score"]
