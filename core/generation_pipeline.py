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
from core.models import Mode, PipelineResult
from core.planning_engine import build_answer_plan, build_cover_letter_plan, build_resume_plan
from core.profile_loader import cached_profile
from core.validators.claim_validator import validate_claims
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
) -> PipelineResult:
    """Run the complete ATS-Ninja v5 generation pipeline."""
    profile = cached_profile()
    parsed_input = parse_input(
        uploaded_resume_pdf=uploaded_resume_pdf,
        resume_text=resume_text,
        job_description=job_description,
        overrides=overrides or {},
        logistics=logistics or {},
        questions_text=questions_text,
        requested_mode=requested_mode,
        profile=profile,
    )
    mode = parsed_input.mode
    if requested_mode == "streamlit_default":
        mode = Mode.RESUME_AND_COVER
    jd_profile = parse_jd(parsed_input.job_description, profile)

    result = PipelineResult(parsed_input=parsed_input, jd_profile=jd_profile)
    resume_plan = None
    if mode in {Mode.RESUME, Mode.RESUME_AND_COVER, Mode.RESUME_AND_QUESTIONS}:
        resume_plan = build_resume_plan(
            contacts=parsed_input.contacts,
            jd_profile=jd_profile,
            profile=profile,
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
        )
        result.resume_plan = resume_plan
        if not result.resume_text:
            result.resume_text = generate_resume_text(resume_plan)
        cover_plan = build_cover_letter_plan(resume_plan, profile)
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
        )
        result.resume_plan = resume_plan
        answer_plan = build_answer_plan(questions=parsed_input.questions, resume_plan=resume_plan)
        result.answer_plan = answer_plan
        result.answers_text = generate_answers_text(answer_plan)
        result.mode_outputs[Mode.QUESTIONS.value] = result.answers_text

    result.validation_errors = validate_pipeline_result(result)
    return result


def validate_pipeline_result(result: PipelineResult) -> list[str]:
    """Run all silent validation gates and return readable errors."""
    profile = cached_profile()
    errors: list[str] = []
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
