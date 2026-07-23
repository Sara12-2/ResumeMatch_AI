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
