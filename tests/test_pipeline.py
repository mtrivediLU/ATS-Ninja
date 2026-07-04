from __future__ import annotations

from core.evidence_engine import classify_keyword
from core.generation_pipeline import mode_from_text, run_pipeline
from core.input_parser import extract_contacts, resolve_contacts
from core.models import Mode
from core.profile_loader import cached_profile
from core.validators.claim_validator import validate_claims
from core.validators.latex_validator import validate_latex
from core.validators.output_format_validator import (
    validate_cover_letter_word_count,
    validate_output_format,
)
from core.validators.style_validator import validate_style


PROFILE = cached_profile()


def test_contact_override_precedence() -> None:
    extracted = extract_contacts("Mihir Trivedi\n249-360-5901\nold@example.com")
    contacts = resolve_contacts(
        overrides={"email": "new@example.com"},
        extracted=extracted,
        profile=PROFILE,
    )
    assert contacts.email == "new@example.com"
    assert contacts.source["email"] == "override"


def test_extracted_resume_contact_used_when_no_override_exists() -> None:
    extracted = extract_contacts("Mihir Trivedi\n705-555-1111\nresume@example.com")
    contacts = resolve_contacts(overrides={}, extracted=extracted, profile=PROFILE)
    assert contacts.email == "resume@example.com"
    assert contacts.phone == "705-555-1111"


def test_profile_default_used_when_no_override_or_extracted_value_exists() -> None:
    contacts = resolve_contacts(overrides={}, extracted=extract_contacts(""), profile=PROFILE)
    assert contacts.email == "mihir1611t@gmail.com"
    assert contacts.name == "Mihir Trivedi"


def test_laurentian_email_rejected() -> None:
    contacts = resolve_contacts(
        overrides={},
        extracted=extract_contacts("Mihir Trivedi\nmtrivedi@laurentian.ca"),
        profile=PROFILE,
    )
    assert contacts.email == "mihir1611t@gmail.com"


def test_default_gmail_used() -> None:
    contacts = resolve_contacts(overrides={}, extracted=extract_contacts(""), profile=PROFILE)
    assert contacts.email == "mihir1611t@gmail.com"


def test_tier_c_cannot_appear_in_experience_bullets() -> None:
    text = "Professional Experience\n- Built FastAPI services.\nEducation"
    assert any("Tier C" in error for error in validate_claims(text, PROFILE))


def test_tier_c_may_appear_in_working_knowledge_line() -> None:
    text = "Technical Skills\nWorking knowledge: FastAPI, GraphQL\nProfessional Experience\n- Built Python pipelines.\nEducation"
    assert not any("Tier C" in error for error in validate_claims(text, PROFILE))


def test_adjacency_phrasing_does_not_become_fake_production_experience() -> None:
    item = classify_keyword("AWS", "required", PROFILE)
    assert item.evidence_tier == "adjacency"
    assert "Azure" in item.real_evidence
    assert "production" not in item.allowed_placement.lower()


def test_unsupported_metric_rejected() -> None:
    errors = validate_claims("Reduced latency by 99% for 1 million users.", PROFILE)
    assert any("unsupported" in error for error in errors)


def test_official_titles_are_not_altered() -> None:
    text = "\\resumeSubheading{Flosonics Medical}{Toronto}{AI Engineer}{Oct 2024 to Apr 2026}"
    assert any("official title altered" in error for error in validate_claims(text, PROFILE))


def test_no_em_dash_en_dash_or_double_hyphen() -> None:
    errors = validate_style("AI engineer — data engineer – software -- resume")
    assert "em dash is not allowed" in errors
    assert "en dash is not allowed" in errors
    assert "double hyphen is not allowed" in errors


def test_banned_words_are_caught() -> None:
    assert any("banned style phrase" in error for error in validate_style("I am excited to apply."))


def test_cover_letter_word_count_is_280_to_320() -> None:
    jd = _sample_jd()
    result = run_pipeline(
        resume_text="Mihir Trivedi\nmihir1611t@gmail.com\n249-360-5901",
        job_description=jd,
        requested_mode="resume and cover letter",
    )
    assert result.cover_letter_plan is not None
    assert 280 <= result.cover_letter_plan.word_count <= 320
    assert not validate_cover_letter_word_count(result.cover_letter_text)


def test_latex_ends_with_end_document() -> None:
    assert "missing \\end{document}" in validate_latex("\\documentclass{article}\n\\begin{document}\nHi")


def test_resume_subheading_has_exactly_4_arguments() -> None:
    good = "\\documentclass{article}\\begin{document}\\resumeSubheading{A}{B}{C}{D}\\end{document}"
    bad = "\\documentclass{article}\\begin{document}\\resumeSubheading{A}{B}{C}\\end{document}"
    assert not any("resumeSubheading" in error for error in validate_latex(good))
    assert any("resumeSubheading" in error for error in validate_latex(bad))


def test_resume_item_has_exactly_1_argument() -> None:
    good = "\\documentclass{article}\\begin{document}\\resumeItem{A}\\end{document}"
    bad = "\\documentclass{article}\\begin{document}\\resumeItem{A}{B}\\end{document}"
    assert not any("resumeItem" in error for error in validate_latex(good))
    assert any("resumeItem" in error for error in validate_latex(bad))


def test_mode_detection_for_resume() -> None:
    assert mode_from_text("", job_description="Python engineer role") == Mode.RESUME


def test_mode_detection_for_cover_letter() -> None:
    assert mode_from_text("please write a cover letter", job_description="JD") == Mode.COVER_LETTER
    assert mode_from_text("CV", job_description="JD") == Mode.COVER_LETTER


def test_mode_detection_for_resume_plus_cover_letter() -> None:
    assert mode_from_text("resume and cover letter", job_description="JD") == Mode.RESUME_AND_COVER


def test_mode_detection_for_application_answers() -> None:
    assert mode_from_text("", questions=["Are you eligible to work in Canada?"]) == Mode.QUESTIONS


def test_mode_detection_for_jd_plus_questions() -> None:
    assert mode_from_text("", job_description="JD", questions=["Why this role?"]) == Mode.RESUME_AND_QUESTIONS


def test_output_format_validator_catches_text_after_final_code_block() -> None:
    text = "**Role:** Test\n**Interview Call Probability:** 80%\n**Analysis:** Good\n```latex\nx\n```\nextra"
    assert any("text after final code block" in error for error in validate_output_format(text, Mode.RESUME))


def _sample_jd() -> str:
    return (
        "Job Title: AI Engineer\n"
        "Company: Northstar Analytics\n"
        "Location: Toronto, Ontario hybrid\n"
        "Required qualifications:\n"
        "- Python for production data and AI systems\n"
        "- SQL and data warehouse experience\n"
        "- LLM integration, prompt engineering, and retrieval workflows\n"
        "- ETL pipelines and stakeholder communication\n"
        "Preferred qualifications:\n"
        "- Azure, Docker, Tableau, Power BI, and Java microservices\n"
        "Responsibilities:\n"
        "- Build internal AI assistants for documents and operational data.\n"
        "- Develop analytics pipelines and reporting for business teams.\n"
        "- Work with engineering and business stakeholders in a regulated environment.\n"
        "This role supports healthcare data operations and requires clear documentation. "
        "The team uses Python, SQL, LLMs, Azure, Docker, Tableau, and ETL patterns."
    )
