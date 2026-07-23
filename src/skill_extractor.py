"""Skill/keyword extraction: spaCy NER + a curated skills taxonomy.

The taxonomy (data/skills_taxonomy.json) is matched against text using
spaCy's PhraseMatcher, which tokenizes through spaCy's pipeline rather
than doing naive substring search - so "AWS" won't false-match inside a
word like "awesome", and matching is case-insensitive on token boundaries.

spaCy's NER (doc.ents) is also run and exposed via extract_entities(), but
it's a supplementary signal: en_core_web_sm's NER is trained for general
entities (organizations, products, people), not technical skills
specifically, so it will not reliably tag things like "Docker" or
"pytest". The taxonomy PhraseMatcher above is what actually drives the
matched/missing/extra skill lists.
"""

import json
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"

_nlp = None
_matcher = None


def _load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_matcher():
    global _matcher
    if _matcher is None:
        nlp = _get_nlp()
        taxonomy = _load_taxonomy()
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        for skills in taxonomy.values():
            for canonical, aliases in skills.items():
                terms = {a.lower() for a in aliases} | {canonical.lower()}
                patterns = [nlp.make_doc(term) for term in terms]
                matcher.add(canonical, patterns)
        _matcher = matcher
    return _matcher


def extract_skills(text: str) -> set:
    """Return the set of canonical taxonomy skill names mentioned in text."""
    nlp = _get_nlp()
    matcher = _get_matcher()
    doc = nlp(text)
    matches = matcher(doc)
    return {nlp.vocab.strings[match_id] for match_id, _start, _end in matches}


def extract_entities(text: str) -> list:
    """Supplementary spaCy NER pass - organizations/products mentioned in
    text. Not used to compute matched/missing skills (see module docstring)."""
    nlp = _get_nlp()
    doc = nlp(text)
    return sorted({ent.text for ent in doc.ents if ent.label_ in ("ORG", "PRODUCT")})


def analyze_skill_gap(resume_text: str, jd_text: str) -> dict:
    """Compare skills found in a resume against skills found in a JD.

    Returns:
        {
          "matched_skills": sorted list - in both resume and JD,
          "missing_skills": sorted list - in JD, not in resume,
          "extra_skills": sorted list - in resume, not in JD,
          "skill_coverage_pct": float 0-100, matched / total JD skills,
        }
    """
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    extra = sorted(resume_skills - jd_skills)

    coverage = round(len(matched) / len(jd_skills) * 100, 2) if jd_skills else 0.0

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "extra_skills": extra,
        "skill_coverage_pct": coverage,
    }
