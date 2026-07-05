from __future__ import annotations

from core.evidence_engine import classify_keyword
from core.generation_pipeline import mode_from_text, run_pipeline
from core.input_parser import extract_contacts, resolve_contacts
from core.models import ContactInfo, Experience, Mode, Profile
from core.validators.claim_validator import validate_claims
from core.validators.latex_validator import validate_latex
from core.validators.output_format_validator import (
    validate_cover_letter_word_count,
    validate_output_format,
)
from core.validators.style_validator import validate_style


def _sample_profile() -> Profile:
    """A synthetic, non-personal profile used only to exercise the generic
    tiering/validation logic, independent of any real candidate's data."""
    return Profile(
        contact=ContactInfo(name="Jordan Rivera", email="jordan@example.com"),
        retired_emails=["old@example.com"],
        role_identities=["Software Engineer"],
        tier_a={"python": "Python", "sql": "SQL", "azure": "Azure"},
        tier_b={"power bi": "Power BI", "data visualization": "data visualization"},
        tier_c={"fastapi": "FastAPI", "graphql": "GraphQL"},
        adjacency={},
        experiences=[
            Experience(
                company="Acme Corp",
                title="Software Engineer",
                location="Remote",
                dates="2020 to 2023",
                bullets=["Built Python pipelines.", "Reduced processing time by 40%."],
            )
        ],
        education=[],
        certifications=[],
        supported_metrics=["40%", "5 hours to minutes"],
    )


PROFILE = _sample_profile()


def test_contact_override_precedence() -> None:
    extracted = extract_contacts("Jordan Rivera\n555-201-9876\nold@example.com")
    contacts = resolve_contacts(
        overrides={"email": "new@example.com"},
        extracted=extracted,
    )
    assert contacts.email == "new@example.com"
    assert contacts.source["email"] == "override"


def test_extracted_resume_contact_used_when_no_override_exists() -> None:
    extracted = extract_contacts("Jordan Rivera\n705-555-1111\nresume@example.com")
    contacts = resolve_contacts(overrides={}, extracted=extracted)
    assert contacts.email == "resume@example.com"
    assert contacts.phone == "705-555-1111"


def test_no_default_identity_when_nothing_provided() -> None:
    contacts = resolve_contacts(overrides={}, extracted=extract_contacts(""))
    assert contacts.email == ""
    assert contacts.name == ""


def test_retired_profile_email_is_rejected() -> None:
    contacts = resolve_contacts(
        overrides={},
        extracted=extract_contacts("Jordan Rivera\nold@example.com"),
        profile=PROFILE,
    )
    assert contacts.email == ""


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


def test_tier_b_skill_is_not_flagged_by_summary_production_word() -> None:
    text = (
        "Professional Summary\n"
        "Software engineer with production software delivery experience.\n"
        "Technical Skills\n"
        "Data and BI: data visualization, Power BI\n"
        "Professional Experience\n"
        "- Built Python pipelines.\n"
        "Education"
    )
    assert not any("data visualization" in error for error in validate_claims(text, PROFILE))


def test_official_titles_are_not_altered() -> None:
    text = "\\resumeSubheading{Acme Corp}{Remote}{Product Manager}{2020 to 2023}"
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
        resume_text=(
            "Jordan Rivera\njordan@example.com\n555-201-9876\n\n"
            "Experience\nAcme Corp Remote\nSoftware Engineer 2020 to 2023\n"
            "- Built Python and SQL data pipelines.\n"
        ),
        job_description=jd,
        requested_mode="resume and cover letter",
        llm=False,
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


# ---------------------------------------------------------------------------
# Regression tests for the upload -> generate failure: the quality gates were
# flagging the candidate's own resume content (banned verbs, scale phrases,
# personal email) and PDF line wrapping was parsed into garbage employers,
# which blocked all output in the app.
# ---------------------------------------------------------------------------

WRAPPED_RESUME_TEXT = (
    "Jordan Rivera\n"
    "555-201-3344 | jordan.rivera@oldschool.edu | linkedin.com/in/jordanrivera\n"
    "PROFESSIONAL EXPERIENCE\n"
    "Acme Analytics Toronto, ON\n"
    "Senior Data Engineer Jan 2020 - Mar 2024\n"
    "- Architected and built a centralized data warehouse using PostgreSQL, creating a\n"
    "unified source of truth serving millions of users across the platform.\n"
    "- Optimized deployment workflows, maintaining 100% uptime for critical\n"
    "production services and reducing release time by 40%.\n"
    "Beta Retail Group Ottawa, ON\n"
    "Data Analyst Jun 2016 - Dec 2019\n"
    "- Built SQL reporting for a team of 12 analysts.\n"
    "EDUCATION\n"
    "Carleton University Ottawa, ON\n"
    "Bachelor of Computer Science 2012 - 2016\n"
)


def test_wrapped_pdf_lines_do_not_become_garbage_employers() -> None:
    from core.resume_extractor import extract_profile

    profile = extract_profile(WRAPPED_RESUME_TEXT)
    companies = [experience.company for experience in profile.experiences]
    assert any("Acme Analytics" in company for company in companies)
    assert any("Beta Retail" in company for company in companies)
    for company in companies:
        assert "unified source of truth" not in company.lower()
        assert "millions of users" not in company.lower()
    first = profile.experiences[0]
    assert first.title == "Senior Data Engineer"
    assert any("millions of users" in bullet for bullet in first.bullets)


def test_pdf_extractor_merges_wrapped_continuation_lines() -> None:
    from core.pdf_extractor import _clean_extracted_text

    text = _clean_extracted_text(
        "- Reduced engineer reporting\ntime from 5 hours to minutes and simplified workflows.\nEDUCATION"
    )
    lines = text.splitlines()
    assert lines[0].endswith("simplified workflows.")
    assert lines[1] == "EDUCATION"


def test_candidates_own_scale_claims_are_supported_evidence() -> None:
    profile = _sample_profile()
    profile.raw_markdown = WRAPPED_RESUME_TEXT
    output = "Professional Experience\n- Maintained 100% uptime serving millions of users.\nEducation"
    errors = validate_claims(output, profile)
    assert not any("unsupported" in error for error in errors)


def test_metrics_not_in_resume_are_flagged() -> None:
    profile = _sample_profile()
    profile.raw_markdown = WRAPPED_RESUME_TEXT
    errors = validate_claims("Increased revenue by 300% for 5 million customers.", profile)
    assert any("300%" in error for error in errors)


def test_soften_banned_style_output_passes_style_validator() -> None:
    from core.output_repair import soften_banned_style

    noisy = (
        "Architected and spearheaded a robust, seamless, mission-critical platform. "
        "Leveraged cutting-edge tools and streamlined end-to-end workflows. "
        "Results-driven and detail-oriented professional passionate about innovative solutions."
    )
    softened = soften_banned_style(noisy)
    assert not validate_style(softened)
    assert "Designed" in softened


def test_full_pipeline_with_resume_containing_banned_words_and_scale_claims() -> None:
    result = run_pipeline(
        resume_text=WRAPPED_RESUME_TEXT,
        job_description=_sample_jd(),
        requested_mode="resume and cover letter",
        llm=False,
    )
    assert result.resume_text
    assert result.cover_letter_text
    assert result.validation_errors == []


def test_email_from_uploaded_resume_is_kept_not_blocked() -> None:
    contacts = extract_contacts(WRAPPED_RESUME_TEXT)
    resolved = resolve_contacts(overrides={}, extracted=contacts)
    assert resolved.email == "jordan.rivera@oldschool.edu"
