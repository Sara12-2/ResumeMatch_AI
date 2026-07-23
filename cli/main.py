"""ResumeMatch AI - CLI.

Usage:
    python cli/main.py --resume sample_data/resume_1.txt --jd sample_data/jd_1.txt
    python cli/main.py --resume path/to/resume.pdf --jd "paste job description text here"
    python cli/main.py --resume resume.txt --jd jd.txt --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.matcher import compute_match_score, section_contributions
from src.parser import load_document, split_into_sections
from src.skill_extractor import analyze_skill_gap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score how well a resume matches a job description."
    )
    parser.add_argument(
        "--resume", required=True, help="Path to a resume file (.pdf or .txt)"
    )
    parser.add_argument(
        "--jd", required=True, help="Path to a JD file (.txt), or raw JD text"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON instead of a text report"
    )
    return parser


def build_report(resume_source, jd_source) -> dict:
    resume_text = load_document(resume_source)
    jd_text = load_document(jd_source)

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


def print_report(report: dict) -> None:
    print(f"Overall Match Score: {report['overall_score']}% ({report['overall_band']})")
    print(f"Skill Coverage:      {report['skill_coverage_pct']}%")
    print()
    print(f"Matched skills ({len(report['matched_skills'])}): "
          f"{', '.join(report['matched_skills']) or '-'}")
    print(f"Missing skills ({len(report['missing_skills'])}): "
          f"{', '.join(report['missing_skills']) or '-'}")
    print(f"Extra skills ({len(report['extra_skills'])}): "
          f"{', '.join(report['extra_skills']) or '-'}")

    if report["section_ranking"]:
        print()
        print("Section contribution (most to least relevant):")
        for s in report["section_ranking"]:
            print(f"  {s['section']:<14} {s['score']:>6}%  {s['band']}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args.resume, args.jd)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
