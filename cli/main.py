"""ResumeMatch AI - CLI.

Usage:
    python cli/main.py --resume sample_data/resume_1.txt --jd sample_data/jd_1.txt
    python cli/main.py --resume path/to/resume.pdf --jd "paste job description text here"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.matcher import compute_match_score
from src.parser import load_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score how well a resume matches a job description."
    )
    parser.add_argument(
        "--resume", required=True, help="Path to a resume file (.pdf or .txt)"
    )
    parser.add_argument(
        "--jd", required=True, help="Path to a job description file (.txt), or raw JD text"
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    resume_text = load_document(args.resume)
    jd_text = load_document(args.jd)

    result = compute_match_score(resume_text, jd_text)

    print(f"Match Score: {result['score']}% ({result['band']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
