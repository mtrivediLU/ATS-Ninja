# ATS-Ninja

ATS-Ninja is a local Streamlit application for generating recruiter-ready resumes, cover letters, and application answers from Mihir Trivedi's v5 profile rules, an uploaded resume PDF or pasted resume text, and a job description.

The current pipeline is designed around truth control first. It resolves contact information, parses the job description, builds an evidence matrix, creates a document plan, generates Overleaf-ready LaTeX, and runs validators before anything is shown to the user.

## What It Does

- Generates ATS-optimized resumes in Mihir's v5 technical resume format.
- Generates one-page cover letters with the same resolved contact identity.
- Generates paste-ready application and screening answers.
- Accepts a resume PDF, pasted resume text, job description, optional application questions, and optional contact/logistics overrides.
- Extracts contact details from uploaded resume text.
- Resolves contacts with strict precedence: user override, uploaded resume, `01_profile_v5.md`, then blank.
- Blocks retired Laurentian email addresses and defaults to `mihir1611t@gmail.com`.
- Shows before and after ATS keyword scores in Streamlit.
- Provides PDF downloads and copyable LaTeX output.

## Pipeline

1. `core/input_parser.py` normalizes resume text, questions, overrides, logistics, mode, and contacts.
2. `core/jd_parser.py` extracts job title, company, work mode, location, required and preferred qualifications, responsibilities, technical keywords, domain, and likely ATS platform.
3. `core/evidence_engine.py` builds a keyword evidence matrix using the v5 gap ladder.
4. `core/planning_engine.py` chooses role identity, summary, skills, bullets, metrics, working knowledge, residual gap, cover-letter angle, and probability.
5. `core/generators/` renders resume LaTeX, cover-letter LaTeX, and application answers from structured plans.
6. `core/validators/` checks truth claims, style, LaTeX structure, cover-letter length, and final output format.

## Truth Tiers

`01_profile_v5.md` is the source of truth.

- Tier A facts can appear in summary, skills, and supported bullets.
- Tier B facts can appear in summary and skills, and in bullets only with careful wording that reflects actual use.
- Tier C facts can appear only in a clearly labeled `Working knowledge` skills line or a cover-letter fast-ramp paragraph.
- Missing facts are never claimed. One residual gap may appear in the analysis snapshot.

The v5 ladder is:

`Tier A exact match > Tier B exact match > adjacency phrasing > Tier C Working knowledge > honest missing gap`

## Validation Gates

The pipeline runs silent gates before returning output:

- Claim validation catches retired emails, Tier C in experience bullets, unsupported metrics, altered official titles, unsupported employers, and production claims for Tier B or Tier C tools.
- Style validation blocks em dashes, en dashes, double hyphens, and banned resume filler language.
- LaTeX validation catches missing `\end{document}`, unbalanced braces, malformed `\resumeSubheading` or `\resumeItem` calls, list mismatches, and code-fence issues.
- Output validation enforces Mode R, Mode C, and Mode Q formatting.
- Cover-letter validation keeps body length between 280 and 320 words.

## Local Setup

Use Python 3.11 or newer.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ollama dependencies remain installed for local model experimentation and compatibility with earlier modules:

```bash
ollama pull llama3.2
```

The v5 production pipeline itself is deterministic and validator-driven so it can enforce truth constraints before output.

## Run The App

```bash
streamlit run app.py
```

Then open the local URL printed by Streamlit.

## Usage

1. Upload a resume PDF or paste resume text.
2. Paste a job description.
3. Optionally paste application questions.
4. Optionally override name, email, phone, headline, location, LinkedIn, website, availability, or work mode.
5. Choose an output mode.
6. Generate materials.
7. Download PDFs or reveal the LaTeX/code text areas.

## Output Modes

- Resume only
- Cover letter only
- Resume and cover letter
- Resume and application answers
- Application answers only

Mode detection helpers are also available in `core/generation_pipeline.py` for programmatic use.

## Tests

Run:

```bash
python -m compileall app.py core
pytest
```

The test suite covers contact precedence, retired email rejection, tier placement, unsupported metrics, official titles, style gates, LaTeX structure, mode detection, cover-letter length, and output format validation.

## Known Limitations

- JD parsing is heuristic, not a full semantic parser.
- The deterministic generator prioritizes truth control over free-form creativity.
- PDF rendering uses WeasyPrint first and ReportLab fallback when native WeasyPrint libraries are unavailable.
- The app does not submit applications or send email.

## License

MIT
