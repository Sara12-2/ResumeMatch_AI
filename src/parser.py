"""Resume/JD text extraction and cleaning.

Supports plain-text (.txt) files and PDFs (.pdf, via pypdf). Callers pass
either a file path or raw text — extract_text() figures out which.
"""

import re
from pathlib import Path

from pypdf import PdfReader


class UnsupportedFileTypeError(Exception):
    pass


def extract_text_from_pdf(file_path) -> str:
    """Extract raw text from a PDF using pypdf's per-page extraction."""
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_text(source) -> str:
    """Return raw text from a .pdf/.txt file path, or pass through raw text.

    If `source` looks like an existing file path, it's read (PDF or plain
    text based on extension). Otherwise `source` is treated as already
    being the document's text (e.g. pasted job description text).
    """
    path = Path(source)
    if path.exists() and path.is_file():
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return extract_text_from_pdf(path)
        if suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="ignore")
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Use .pdf or .txt, or pass raw text."
        )
    return str(source)


def clean_text(text: str) -> str:
    """Collapse whitespace/newlines so downstream NLP sees normalized text."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def load_document(source) -> str:
    """extract_text() + clean_text() in one call — the normal entry point."""
    return clean_text(extract_text(source))


# Common resume section headers, lowercased. Section detection is a
# heuristic line-match against this list, not a general-purpose resume
# parser - unusual or missing headers just fall under "Header" (see
# README Limitations).
SECTION_HEADERS = {
    "summary", "objective", "profile", "about", "about me",
    "skills", "technical skills", "core competencies", "key skills",
    "experience", "work experience", "professional experience",
    "employment history", "work history",
    "education", "academic background",
    "projects", "personal projects", "key projects",
    "certifications", "certificates", "licenses",
    "achievements", "awards", "accomplishments",
}

_HEADER_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z /&-]{1,40}$")


def split_into_sections(text: str) -> dict:
    """Split resume text into sections keyed by detected header name.

    Scans for short standalone lines matching a known header (case-
    insensitive, see SECTION_HEADERS). Text before the first detected
    header - and the whole resume, if no header is recognized - is
    grouped under "Header".
    """
    sections: dict[str, list[str]] = {"Header": []}
    current = "Header"

    for line in text.split("\n"):
        stripped = line.strip().rstrip(":")
        if stripped.lower() in SECTION_HEADERS and _HEADER_LINE_RE.match(stripped):
            current = stripped.title()
            sections.setdefault(current, [])
            continue
        sections[current].append(line)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}
