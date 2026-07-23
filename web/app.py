"""ResumeMatch AI - Flask web interface.

Run with:
    python web/app.py
Then open http://localhost:5000. Port and debug mode can be overridden
with the PORT and FLASK_DEBUG environment variables.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from flask import Flask, render_template, request

from src.matcher import EmptyDocumentError, compute_match_score, section_contributions
from src.parser import UnsupportedFileTypeError, load_document, split_into_sections
from src.recommender import RecommenderError, generate_suggestions
from src.skill_extractor import analyze_skill_gap

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB uploads

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"
SAMPLE_PAIRS = [
    {"id": 1, "label": "Backend Engineer (strong match)"},
    {"id": 2, "label": "Data Analyst (strong match)"},
    {"id": 3, "label": "Frontend Developer (strong match)"},
    {"id": 4, "label": "DevOps Engineer (strong match)"},
    {"id": 5, "label": "Marketing vs. ML Engineer (mismatch demo)"},
]


def _load_sample_pairs() -> list:
    """Read sample_data/ pairs fresh on each request - it's 5 small text
    files, cheap enough to not bother caching."""
    pairs = []
    for pair in SAMPLE_PAIRS:
        resume_path = SAMPLE_DIR / f"resume_{pair['id']}.txt"
        jd_path = SAMPLE_DIR / f"jd_{pair['id']}.txt"
        if resume_path.exists() and jd_path.exists():
            pairs.append({
                "id": pair["id"],
                "label": pair["label"],
                "resume": resume_path.read_text(encoding="utf-8"),
                "jd": jd_path.read_text(encoding="utf-8"),
            })
    return pairs


def _resolve_input(file_storage, pasted_text: str) -> str:
    """Return document text from an uploaded file if present, else pasted text."""
    if file_storage and file_storage.filename:
        suffix = Path(file_storage.filename).suffix.lower() or ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            file_storage.save(tmp.name)
            tmp_path = tmp.name
        try:
            return load_document(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    return load_document(pasted_text or "")


def _build_result(resume_text: str, jd_text: str) -> dict:
    overall = compute_match_score(resume_text, jd_text)
    skills = analyze_skill_gap(resume_text, jd_text)
    ranked_sections = section_contributions(split_into_sections(resume_text), jd_text)

    return {
        "overall_score": overall["score"],
        "overall_band": overall["band"],
        "matched_skills": skills["matched_skills"],
        "missing_skills": skills["missing_skills"],
        "extra_skills": skills["extra_skills"],
        "skill_coverage_pct": skills["skill_coverage_pct"],
        "section_ranking": ranked_sections,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        try:
            resume_text = _resolve_input(
                request.files.get("resume_file"), request.form.get("resume_text", "")
            )
            jd_text = _resolve_input(
                request.files.get("jd_file"), request.form.get("jd_text", "")
            )
            result = _build_result(resume_text, jd_text)

            if request.form.get("narrative"):
                try:
                    result["narrative"] = generate_suggestions(result)
                except RecommenderError as exc:
                    result["narrative_error"] = str(exc)
        except (EmptyDocumentError, UnsupportedFileTypeError) as exc:
            error = str(exc)
        except Exception:
            error = "Could not process the uploaded files. Please check the format and try again."

    return render_template(
        "index.html",
        result=result,
        error=error,
        sample_pairs_json=json.dumps(_load_sample_pairs()),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
