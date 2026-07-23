## ResumeMatch AI

[![CI](https://github.com/Sara12-2/ResumeMatch_AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Sara12-2/ResumeMatch_AI/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)

Scores how well a resume matches a specific job description using classical
NLP — TF-IDF vectorization and cosine similarity for the match score, spaCy
NER + a curated skills taxonomy for gap analysis — and surfaces exactly which
skills are missing and which resume sections are pulling the score down. No
LLM call is required for any of that: it's deterministic, offline, and free
to run at scale. An **optional** Groq-powered layer can turn the raw gap
analysis into natural-language improvement suggestions, but the app is fully
functional without it.

### The problem this solves

| Problem | What ResumeMatch AI does |
|---|---|
| "Does my resume actually match this job?" is a guess | Gives a reproducible 0-100% score from the actual text, not a vibe |
| Resumes get rejected for missing keywords the candidate didn't realize mattered | Lists the exact skills present in the JD but absent from the resume |
| Generic "add more keywords" advice isn't actionable | Ranks which resume *sections* (Skills, Experience, Education, ...) are helping or hurting the score |
| LLM-based tools require an API key and cost money per resume | Core scoring is TF-IDF + cosine similarity - runs fully offline, no API key needed |

## Architecture

```
                    ┌────────────────────┐
   resume (.pdf/.txt) ─▶│                    │
                    │   src/parser.py    │──▶ cleaned text + detected sections
   job desc (.txt)   ─▶│  (extract + clean) │
                    └────────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
     ┌───────────────────────┐   ┌─────────────────────────┐
     │   src/matcher.py      │   │  src/skill_extractor.py │
     │ TF-IDF + cosine sim   │   │ spaCy NER + taxonomy    │
     │ (deterministic core)  │   │ PhraseMatcher           │
     └───────────────────────┘   └─────────────────────────┘
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                  overall score, band, section
                  ranking, matched/missing/
                  extra skills  (this is the
                  complete, self-sufficient
                  output - everything above
                  runs with zero network calls)
                               │
                               ▼  (optional, only if --narrative
                                   / checkbox is set AND
                                   GROQ_API_KEY is configured)
                  ┌─────────────────────────┐
                  │   src/recommender.py    │
                  │  Groq narrative layer   │
                  └─────────────────────────┘
                               │
                               ▼
                 cli/main.py (text or --json)
                 web/app.py  (Flask results page)
```

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Match scoring | `scikit-learn` `TfidfVectorizer` + `cosine_similarity` | The deterministic core - see "How the matching actually works" below |
| Skill extraction | `spaCy` (`en_core_web_sm`) `PhraseMatcher` + curated JSON taxonomy | Taxonomy phrase-matching drives matched/missing/extra; spaCy NER is a secondary, documented signal (see Limitations) |
| PDF parsing | `pypdf` | Per-page text extraction |
| Web interface | `Flask` + vanilla JS + CSS | Server-rendered single-page form/results, drag-and-drop uploads, glassmorphic UI with light/dark theme support, inline SVG icons (no icon font/CDN, no emoji) |
| CLI | `argparse` | Text or `--json` output for scripting |
| Optional narrative layer | `groq` Python SDK | Only imported/called if `--narrative`/checkbox is used; app works fully without it |
| Testing | `pytest` | 16 tests across matcher, skill extractor, recommender |
| CI | GitHub Actions | Runs the full suite on every push/PR to `main` |

## How the matching actually works

**Overall score** (`src/matcher.py`): the resume and JD text are fit into a
single `TfidfVectorizer` corpus of two documents, then scored with cosine
similarity:

```python
TfidfVectorizer(stop_words="english", ngram_range=(1, 1), sublinear_tf=True, lowercase=True)
```

- **Unigrams only, no bigrams.** We tried `ngram_range=(1, 2)` first - it made
  the score too sensitive to exact phrasing (the same skills described in
  different words scored much lower), which produced misleadingly low
  matches. Unigrams measure vocabulary overlap, not phrase order.
- **Score bands** (`src/config.py`): `>= 45` Strong, `>= 25` Moderate, `< 25`
  Weak. These were tuned against the synthetic pairs in `tests/test_matcher.py`
  and the real `sample_data/` pairs, not picked arbitrarily. Whole-document
  TF-IDF cosine similarity is lexical - two independently-written documents
  rarely share more than ~40-60% weighted vocabulary even when the underlying
  skills genuinely match (see the real example below), so the bands are
  calibrated lower than you might intuitively expect.

**Skill extraction** (`src/skill_extractor.py`): `data/skills_taxonomy.json`
is a curated dictionary of ~70 skills across 8 categories (languages,
frameworks, databases, cloud/devops, data & ML, tools, testing, soft skills),
each with alias lists (e.g. `"postgres"` → `PostgreSQL`, `"k8s"` →
`Kubernetes`). Aliases are compiled into a spaCy `PhraseMatcher` and matched
against the tokenized text - matching through spaCy's tokenizer (not naive
substring search) means `"AWS"` won't false-match inside `"awesome"`, and
matching is case-insensitive on token boundaries. `matched_skills` /
`missing_skills` / `extra_skills` are just set operations on the two
extracted skill sets. spaCy's NER (`doc.ents`) also runs and is exposed via
`extract_entities()`, but it's a **secondary** signal - `en_core_web_sm` is
trained for general entities (organizations, people, places), not technical
skills, so it won't reliably tag things like `"Docker"` or `"pytest"`. The
taxonomy `PhraseMatcher` is what actually drives every matched/missing/extra
list in this project.

**Section contribution** (`src/parser.py` + `src/matcher.py`): resume text is
split on a heuristic match against ~20 common header strings (Summary,
Skills, Experience, Education, Projects, ...). Each detected section is
scored against the JD using the same TF-IDF function above, then ranked.

## Real example output

Run yourself:
```bash
python cli/main.py --resume sample_data/resume_1.txt --jd sample_data/jd_1.txt
```

Output (unedited):
```
Overall Match Score: 37.85% (Moderate Match)
Skill Coverage:      66.67%

Matched skills (10): AWS, Django, Docker, Flask, Git, PostgreSQL, Python, REST API, Redis, pytest
Missing skills (5): CI/CD, GitHub Actions, GraphQL, Jenkins, Kubernetes
Extra skills (2): Linux, Unit Testing

Section contribution (most to least relevant):
  Skills          29.74%  Moderate Match
  Experience      28.59%  Moderate Match
  Summary         23.48%  Weak Match
  Header          12.03%  Weak Match
  Projects         8.71%  Weak Match
  Education        3.63%  Weak Match
```

Notice the gap between the overall score (37.85%, "Moderate") and skill
coverage (66.67%, 10/15 skills matched) - this is real, not a bug. TF-IDF
cosine similarity over whole documents is lexical and penalizes different
phrasing/structure, while the taxonomy-based skill view captures what a
recruiter usually cares about more directly. This is exactly why both layers
exist: the score alone would undersell a genuinely solid match.

`sample_data/` also includes a **deliberately mismatched** pair
(`resume_5.txt`, a Marketing Coordinator resume, against `jd_5.txt`, a
Machine Learning Engineer JD) to demonstrate the other end of the scale:

```
Overall Match Score: 4.05% (Weak Match)
Skill Coverage:      0.0%
Matched skills (0): -
Missing skills (11): AWS, Docker, Kubernetes, NLTK, NumPy, Pandas, PyTorch, Python, TensorFlow, scikit-learn, spaCy
Extra skills (3): Communication, Project Management, Teamwork
```

## Project structure

```
ResumeMatch_AI/
├── src/
│   ├── parser.py            # PDF/text extraction, cleaning, section splitting
│   ├── matcher.py            # TF-IDF + cosine similarity (deterministic core)
│   ├── skill_extractor.py     # spaCy NER + taxonomy PhraseMatcher
│   ├── recommender.py         # Optional Groq narrative layer, graceful fallback
│   └── config.py              # TF-IDF params + score-band thresholds
├── web/
│   ├── app.py                 # Flask interface
│   └── templates/index.html
├── cli/
│   └── main.py                 # CLI (text or --json output)
├── data/
│   └── skills_taxonomy.json    # Curated skills dictionary
├── sample_data/                 # 5 synthetic resume/JD pairs (see above)
├── tests/
│   ├── test_matcher.py
│   ├── test_skill_extractor.py
│   └── test_recommender.py
├── .github/workflows/ci.yml
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

> If `spacy download` fails with a dependency error mentioning `click`, an
> unpinned install pulled in a `typer` version too new for spaCy 3.7's CLI.
> `requirements.txt` already pins `typer<0.10` and `click<9.0` to prevent
> this - just make sure you installed from `requirements.txt` before running
> the download command.

**CLI:**
```bash
python cli/main.py --resume sample_data/resume_1.txt --jd sample_data/jd_1.txt
python cli/main.py --resume resume.pdf --jd jd.txt --json
python cli/main.py --resume resume.txt --jd jd.txt --narrative   # requires GROQ_API_KEY
```

**Web:**
```bash
python web/app.py
```
Then open `http://localhost:5000`. Port and debug mode can be overridden with
the `PORT` and `FLASK_DEBUG` environment variables.

The web UI (`web/templates/index.html`) supports drag-and-drop file upload
(or paste text directly), a "Try an example" dropdown that instantly loads
one of the 5 `sample_data/` pairs into both fields, a circular match-score
indicator, and color-coded skill/section tags. It's a glassmorphic design
(translucent, blurred panels over a gradient background) with hover/focus
transitions throughout, fully responsive (single column below ~720px), and
automatically follows the OS light/dark theme via `prefers-color-scheme` -
verified in both modes, not just the default. Icons are hand-written inline
SVG throughout - no icon font, no CDN, no emoji - keeping the "runs fully
offline" claim true for the browser too, not just the scoring engine.

**Optional narrative layer:** copy `.env.example` to `.env` and set
`GROQ_API_KEY` (get one free at [console.groq.com](https://console.groq.com)).
Without it, everything above still works - the CLI `--narrative` flag and web
checkbox just print/render "Narrative suggestions skipped: GROQ_API_KEY is
not set" instead of a narrative.

**Tests:**
```bash
pytest tests/ -v
```
16 tests covering known-input/known-output score ranges, empty-document
edge cases, skill-extraction alias matching, section ranking, and the
recommender's graceful-degradation contract (verified without hitting the
network).

## Limitations

Stated honestly, not hidden:

- **The skills taxonomy is a fixed, curated list (~70 skills, 8 categories).**
  A skill not in `data/skills_taxonomy.json` is invisible to the matcher,
  even if it's genuinely relevant. It is not exhaustive and skews toward
  software/data roles.
- **No understanding of seniority, context, or recency.** "5 years leading a
  Python team" and "took a one-week Python course" both just register as
  "Python" - the matcher can't tell competence level or how recent experience
  is.
- **spaCy NER is a secondary, not primary, signal.** `en_core_web_sm` is a
  general-purpose model (organizations, people, places), not fine-tuned for
  technical skills - `extract_entities()` exists but does not drive the
  matched/missing/extra lists.
- **TF-IDF is lexical, not semantic.** It measures vocabulary overlap, not
  meaning - "built REST APIs" and "designed HTTP interfaces" describe the same
  thing but share almost no vocabulary, so paraphrased resumes can score lower
  than the underlying skill match would suggest. This is also exactly why the
  skill-extraction layer exists alongside the score, rather than replacing it.
- **PDF parsing quality varies by resume format.** `pypdf`'s text extraction
  can produce jumbled or missing text for resumes with multi-column layouts,
  tables, or embedded images/icons - a known limitation of PDF text
  extraction generally, not specific to this project.
- **Section detection is heuristic.** It matches against a list of ~20 common
  header strings; resumes with unconventional or missing headers fall
  entirely under a single "Header" bucket instead of being split out.
- **The optional Groq layer is not evaluated for suggestion quality.** It's
  wired up and gracefully degrades when unconfigured, but the actual
  usefulness of its suggestions hasn't been systematically tested against a
  live API key.
