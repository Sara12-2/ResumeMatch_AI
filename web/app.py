"""ResumeMatch AI - Flask web interface.

Run with:
    python web/app.py
Then open http://localhost:5000. Port and debug mode can be overridden
with the PORT and FLASK_DEBUG environment variables.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, request

from src.matcher import EmptyDocumentError, compute_match_score, section_contributions
from src.parser import UnsupportedFileTypeError, load_document, split_into_sections
from src.skill_extractor import analyze_skill_gap

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB uploads


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
        except (EmptyDocumentError, UnsupportedFileTypeError) as exc:
            error = str(exc)
        except Exception:
            error = "Could not process the uploaded files. Please check the format and try again."

    return render_template("index.html", result=result, error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
