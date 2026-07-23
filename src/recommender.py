"""Optional natural-language improvement suggestions via Groq.

This layer is entirely optional - the app is fully functional without it.
The match score (src/matcher.py) and skill gap analysis
(src/skill_extractor.py) never depend on this module or call an LLM.

If GROQ_API_KEY isn't set, or the API call fails for any reason, callers
should catch RecommenderError and just omit the narrative section rather
than crash - see cli/main.py and web/app.py for the fallback pattern.
"""

import os

from groq import Groq

_client = None

SYSTEM_PROMPT = (
    "You are a career coach helping a candidate improve their resume for a "
    "specific job description. You will be given their overall match score, "
    "matched skills, missing skills, and extra skills. Write 3-5 short, "
    "concrete, encouraging suggestions for improving the resume for this "
    "specific role. Do not invent skills or experience the candidate "
    "doesn't have - only suggest how to better surface existing experience, "
    "or which missing skills to prioritize learning or highlighting. Keep "
    "the whole response under 200 words."
)


class RecommenderError(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RecommenderError(
                "GROQ_API_KEY is not set. Add it to .env (see .env.example) "
                "to enable narrative suggestions - this layer is optional."
            )
        _client = Groq(api_key=api_key)
    return _client


def generate_suggestions(report: dict) -> str:
    """Turn a deterministic match report into narrative suggestions.

    `report` is the dict produced by cli/main.py's build_report() /
    web/app.py's _build_result() (overall_score, overall_band,
    matched_skills, missing_skills, extra_skills, skill_coverage_pct).

    Raises RecommenderError if GROQ_API_KEY isn't configured or the
    request fails - the deterministic score/skills report is unaffected
    either way.
    """
    client = _get_client()
    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    user_prompt = (
        f"Overall match score: {report['overall_score']}% ({report['overall_band']})\n"
        f"Skill coverage: {report['skill_coverage_pct']}%\n"
        f"Matched skills: {', '.join(report['matched_skills']) or 'none'}\n"
        f"Missing skills: {', '.join(report['missing_skills']) or 'none'}\n"
        f"Extra skills (on the resume but not requested by the JD): "
        f"{', '.join(report['extra_skills']) or 'none'}\n"
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
    except Exception as e:
        raise RecommenderError(f"Groq request failed: {e}")

    return completion.choices[0].message.content.strip()
