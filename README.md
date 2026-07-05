# ATS-Ninja

ATS-Ninja is a local Streamlit application that tailors a resume, cover letter, and application answers to a specific job description, from just two inputs: an uploaded resume PDF and a pasted job description. It works for any candidate: nothing about the pipeline is hardcoded to one person's facts.

The pipeline is designed around truth control first. It parses the candidate's own resume into a structured, tiered profile, parses the job description, builds an evidence matrix, creates a document plan, generates Overleaf-ready LaTeX, and runs validators before anything is shown to the user. Every claim in the output traces back to something literally present in the uploaded resume.

## What It Does

- Extracts a structured, tiered candidate profile from the uploaded resume PDF: contacts, experience with bullets, education, and certifications.
- Tailors a resume, one-page cover letter, and paste-ready application answers to a specific job description.
- Uses a local Ollama model (when reachable) to raise generation quality: JD extraction, resume summary, bullet rewriting, and cover-letter prose.
- Falls back to deterministic, validator-checked generation when Ollama is not running, so the app always produces valid output.
- Shows before and after ATS keyword scores, plus a keyword match analysis.
- Provides PDF downloads and copyable LaTeX output.

## Pipeline

1. `core/input_parser.py` extracts contact fields from the uploaded resume text; there is no default identity, a field stays blank if it truly is not present.
2. `core/resume_extractor.py` builds the candidate's `Profile`: experiences, education, certifications, and a tiered skill inventory. An LLM extraction pass is used when Ollama is reachable, with a deterministic heuristic parser as a fallback; either way every experience/bullet is checked against the source resume text before being trusted.
3. `core/jd_parser.py` extracts job title, company, work mode, location, required and preferred qualifications, responsibilities, technical keywords, domain, and likely ATS platform, using the same LLM-first/heuristic-fallback pattern.
4. `core/evidence_engine.py` builds a keyword evidence matrix using the gap ladder below, pairing any JD tool the candidate lacks with a real tool they used in the same category (see `core/adjacency_map.py`).
5. `core/planning_engine.py` chooses a role identity from the candidate's own past titles, then builds the summary, skills, bullets, cover-letter body, and answers. Every LLM-generated piece of prose is validated (style rules, no invented metrics/tools) and retried once before falling back to a deterministic version.
6. `core/generators/` renders resume LaTeX, cover-letter LaTeX, and application answers from the structured plans.
7. `core/validators/` checks truth claims, style, LaTeX structure, cover-letter length, and final output format.

## Skill Tiers

Tiers are derived from the candidate's own resume, not hand-maintained:

- **Tier A**: a skill that appears in an actual experience bullet (demonstrated, not just listed). Can appear anywhere: summary, skills, bullets.
- **Tier B**: a skill mentioned in the resume's summary/objective but not shown in a bullet. Can appear in summary and skills.
- **Tier C**: a skill listed only in a flat skills section, with no demonstrated evidence anywhere else. Can only appear on a clearly labeled `Working knowledge` skills line, never in experience bullets.
- Missing: a JD requirement with no match anywhere in the candidate's tiers and no honest adjacency. Never claimed; named once in the analysis snapshot.

The gap ladder for a required JD keyword is:

`Tier A exact match > Tier B exact match > adjacency phrasing (same tool category, real tool named) > Tier C "Working knowledge" line > honest missing gap`

## Validation Gates

The pipeline runs silent gates before returning output:

- Claim validation catches retired/banned emails, Tier C claims in experience bullets, unsupported metrics, altered official titles, and employers not present in the candidate's own resume.
- Style validation blocks em dashes, en dashes, double hyphens, and banned resume filler language.
- LaTeX validation catches missing `\end{document}`, unbalanced braces, malformed `\resumeSubheading` or `\resumeItem` calls, list mismatches, and code-fence issues.
- Output validation enforces Mode R, Mode C, and Mode Q formatting.
- Cover-letter validation keeps body length between 280 and 320 words.

## Performance

Local LLM inference is the slow part of this pipeline, so latency was optimized directly:

- **Line-number extraction**: resume and JD parsing ask the model to point at line numbers for bullets/requirements instead of retyping them, then Python resolves the exact source text. This is both faster (far fewer output tokens to decode) and more grounded (the resolved text is a guaranteed verbatim slice of the source, not a paraphrase).
- **Batched bullet rewriting**: every selected bullet across every experience is rewritten in a single LLM call instead of one call per bullet.
- **Concurrent independent stages**: profile extraction and JD parsing run in parallel threads, as do summary writing and bullet rewriting, and per-question answers. These are I/O-bound calls to the local model server, so threading overlaps them at no extra cost; if your Ollama instance supports concurrent request handling (`OLLAMA_NUM_PARALLEL`), this yields real wall-clock savings.
- **Tuned output budgets**: a larger-output client handles bulk JSON extraction/rewrite calls, a smaller-output client handles short prose (summary, cover letter, answers), so no call generates more tokens than its task needs.
- **On-disk response cache** (`core/llm_cache.py`, via `diskcache`): identical (model, prompt) pairs are cached, so re-generating with the same resume and JD (a very common workflow) is near-instant. Use the "Force fresh generation" checkbox in the sidebar, or set `ATS_NINJA_LLM_CACHE=0`, to bypass it.

If generation still feels slow, the model itself is usually the bottleneck: try a smaller/faster local model, or set `OLLAMA_NUM_PARALLEL` on the Ollama server if your hardware can support concurrent requests.

## Local Setup

Use Python 3.11 or newer.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For higher-quality generation, run a local Ollama model:

```bash
ollama pull llama3.2
ollama serve
```

The app works without Ollama running; it just uses the deterministic fallback path for JD parsing, summary/bullet writing, and cover-letter prose.

## Run The App

```bash
streamlit run app.py
```

Then open the local URL printed by Streamlit.

## Usage

1. Upload a resume PDF.
2. Paste a job description.
3. Choose `llama3.2` or `qwen2.5:7b` (only used if Ollama is reachable).
4. Generate materials.
5. Download PDFs or reveal the LaTeX/code text areas.

## Output Modes

- The Streamlit UI generates a resume and cover letter together.
- The underlying pipeline also supports resume-only, cover-letter-only, and application-answer modes programmatically through `core/generation_pipeline.py` (see `requested_mode`, e.g. `"cover letter"`, `"resume and cover letter"`, or passing `questions_text`).

## Tests

Run:

```bash
python -m compileall app.py core
pytest
```

The test suite covers contact precedence, retired email rejection, tier placement, unsupported metrics, official titles, style gates, LaTeX structure, mode detection, cover-letter length, and output format validation.

## Known Limitations

- Resume and JD parsing are materially better with Ollama reachable; the no-LLM fallback is heuristic and less nuanced on unusually formatted resumes.
- PDF rendering uses WeasyPrint first and ReportLab fallback when native WeasyPrint libraries are unavailable.
- The app does not submit applications or send email.

## License

MIT
