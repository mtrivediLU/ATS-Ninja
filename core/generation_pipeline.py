from __future__ import annotations

from typing import Any

from core.generators.answer_generator import generate_answers_text
from core.generators.cover_letter_generator import (
    format_cover_letter_output,
    generate_cover_letter_latex,
    generate_cover_letter_text,
)
from core.generators.resume_generator import (
    format_resume_output,
    generate_resume_latex,
    generate_resume_text,
)
from core.input_parser import detect_mode, parse_input
from core.jd_parser import parse_jd
from core.llm import get_llm_pair, run_concurrently
from core.models import Mode, PipelineResult
from core.planning_engine import build_answer_plan, build_cover_letter_plan, build_resume_plan
from core.profile_loader import build_profile
from core.validators.claim_validator import validate_claims
from core.validators.completeness_validator import validate_completeness
from core.validators.latex_validator import validate_latex
from core.validators.output_format_validator import (
    validate_cover_letter_word_count,
    validate_output_format,
)
from core.validators.style_validator import validate_style


def run_pipeline(
    *,
    uploaded_resume_pdf: Any | None = None,
    resume_text: str = "",
    job_description: str = "",
    overrides: dict[str, str] | None = None,
    logistics: dict[str, str] | None = None,
    questions_text: str = "",
    requested_mode: str = "",
    model_name: str = "",
    llm: Any | None = None,
) -> PipelineResult:
    """Run the complete ATS-Ninja generation pipeline.

    Every fact used to build the resume, cover letter, and answers comes
    from the candidate's own uploaded resume text (parsed into a Profile)
    plus the job description. No hardcoded personal data is involved. When
    a local Ollama model is reachable it is used to raise generation
    quality; when it is not, every step falls back to deterministic,
    validator-checked logic so the app keeps working.

    Two differently-tuned model clients are used internally: a larger
    output-budget client for the bulk JSON extraction/rewrite calls (resume
    parsing, JD parsing, batched bullet rewriting) and a smaller one for
    short prose (summary, cover letter, answers). This keeps latency down
    without truncating the calls that legitimately need more room.
    """
    parsed_input = parse_input(
        uploaded_resume_pdf=uploaded_resume_pdf,
        resume_text=resume_text,
        job_description=job_description,
        overrides=overrides or {},
        logistics=logistics or {},
        questions_text=questions_text,
        requested_mode=requested_mode,
    )
    mode = parsed_input.mode
    if requested_mode == "streamlit_default":
        mode = Mode.RESUME_AND_COVER

    if llm is False:  # explicit opt-out (e.g. tests forcing the deterministic path)
        extraction_llm, prose_llm = None, None
    elif llm is not None:  # explicit override (e.g. a caller-supplied client): use it everywhere
        extraction_llm, prose_llm = llm, llm
    else:
        extraction_llm, prose_llm = get_llm_pair(model_name=model_name or "llama3.2")

    profile, jd_profile = _parse_profile_and_jd(parsed_input, extraction_llm)

    result = PipelineResult(parsed_input=parsed_input, jd_profile=jd_profile)
    result.metadata["llm_available"] = extraction_llm is not None
    resume_plan = None
    if mode in {Mode.RESUME, Mode.RESUME_AND_COVER, Mode.RESUME_AND_QUESTIONS}:
        resume_plan = build_resume_plan(
            contacts=parsed_input.contacts,
            jd_profile=jd_profile,
            profile=profile,
            llm=prose_llm,
            batch_llm=extraction_llm,
        )
        result.resume_plan = resume_plan
        result.resume_text = generate_resume_text(resume_plan)
        result.resume_latex = generate_resume_latex(resume_plan)
        result.mode_outputs[Mode.RESUME.value] = format_resume_output(
            resume_plan,
            result.resume_latex,
        )

    if mode in {Mode.COVER_LETTER, Mode.RESUME_AND_COVER}:
        resume_plan = resume_plan or build_resume_plan(
            contacts=parsed_input.contacts,
            jd_profile=jd_profile,
            profile=profile,
            llm=prose_llm,
            batch_llm=extraction_llm,
        )
        result.resume_plan = resume_plan
        if not result.resume_text:
            result.resume_text = generate_resume_text(resume_plan)
        cover_plan = build_cover_letter_plan(resume_plan, profile, llm=prose_llm)
        result.cover_letter_plan = cover_plan
        result.cover_letter_text = generate_cover_letter_text(cover_plan)
        result.cover_letter_latex = generate_cover_letter_latex(cover_plan)
        result.mode_outputs[Mode.COVER_LETTER.value] = format_cover_letter_output(
            cover_plan,
            result.cover_letter_latex,
        )

    if mode in {Mode.QUESTIONS, Mode.RESUME_AND_QUESTIONS}:
        resume_plan = resume_plan or build_resume_plan(
            contacts=parsed_input.contacts,
            jd_profile=jd_profile,
            profile=profile,
            llm=prose_llm,
            batch_llm=extraction_llm,
        )
        result.resume_plan = resume_plan
        answer_plan = build_answer_plan(questions=parsed_input.questions, resume_plan=resume_plan, llm=prose_llm)
        result.answer_plan = answer_plan
        result.answers_text = generate_answers_text(answer_plan)
        result.mode_outputs[Mode.QUESTIONS.value] = result.answers_text

    result.validation_errors = validate_pipeline_result(result, profile)
    return result


def _parse_profile_and_jd(parsed_input: Any, extraction_llm: Any | None) -> tuple[Any, Any]:
    """Build the candidate profile and parse the JD.

    Both are independent LLM calls, so when a model is available they run
    concurrently. Without a model, this is all fast heuristics anyway, and
    running profile extraction first lets JD parsing's heuristic fallback
    use the candidate's own tiered vocabulary for keyword matching.
    """
    if extraction_llm is None:
        profile = build_profile(parsed_input.resume_text, llm=None)
        jd_profile = parse_jd(parsed_input.job_description, profile=profile, llm=None)
        return profile, jd_profile

    results = run_concurrently(
        {
            "profile": lambda: build_profile(parsed_input.resume_text, llm=extraction_llm),
            "jd_profile": lambda: parse_jd(parsed_input.job_description, profile=None, llm=extraction_llm),
        }
    )
    return results["profile"], results["jd_profile"]


def validate_pipeline_result(result: PipelineResult, profile: Any | None = None) -> list[str]:
    """Run all silent validation gates and return readable errors."""
    if profile is None:
        profile = build_profile(result.parsed_input.resume_text)
    errors: list[str] = []
    errors.extend(validate_completeness(result, profile))
    if result.resume_latex:
        errors.extend([f"resume: {error}" for error in validate_latex(result.resume_latex)])
        errors.extend([f"resume: {error}" for error in validate_style(result.resume_latex)])
        errors.extend([f"resume: {error}" for error in validate_claims(result.resume_latex, profile)])
        errors.extend(
            [f"resume output: {error}" for error in validate_output_format(result.mode_outputs[Mode.RESUME.value], Mode.RESUME)]
        )
    if result.cover_letter_latex:
        errors.extend([f"cover letter: {error}" for error in validate_latex(result.cover_letter_latex)])
        errors.extend([f"cover letter: {error}" for error in validate_style(result.cover_letter_latex)])
        errors.extend([f"cover letter: {error}" for error in validate_claims(result.cover_letter_latex, profile)])
        errors.extend(
            [
                f"cover letter: {error}"
                for error in validate_cover_letter_word_count(result.cover_letter_text)
            ]
        )
        errors.extend(
            [
                f"cover letter output: {error}"
                for error in validate_output_format(
                    result.mode_outputs[Mode.COVER_LETTER.value],
                    Mode.COVER_LETTER,
                )
            ]
        )
    if result.answers_text:
        errors.extend([f"answers: {error}" for error in validate_style(result.answers_text)])
        errors.extend(
            [f"answers output: {error}" for error in validate_output_format(result.answers_text, Mode.QUESTIONS)]
        )
    return _dedupe(errors)


def mode_from_text(requested_text: str, job_description: str = "", questions: list[str] | None = None) -> Mode:
    """Public helper for tests and callers that only need mode detection."""
    return detect_mode(
        requested_text=requested_text,
        job_description=job_description,
        questions=questions or [],
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out
