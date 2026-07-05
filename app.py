from __future__ import annotations

import os
import time
from typing import Any

import streamlit as st

from core.ats_scorer import calculate_ats_score, compare_scores, extract_keywords
from core.generation_pipeline import run_pipeline
from core.llm import test_ollama_connection
from core.pdf_extractor import extract_text_from_pdf
from core.pdf_generator import generate_cover_letter_pdf, generate_resume_pdf
from core.resume_generator import generate_resume_keywords_analysis


MODEL_OPTIONS = ["llama3.2", "qwen2.5:7b"]


def initialize_state() -> None:
    """Initialize Streamlit session state keys used by the application."""
    st.session_state.setdefault("generated", None)
    st.session_state.setdefault("show_resume_latex", False)
    st.session_state.setdefault("show_cover_latex", False)


def score_color(score: float) -> str:
    """Return a display color for an ATS score."""
    if score < 60:
        return "#b42318"
    if score <= 80:
        return "#b54708"
    return "#027a48"


def render_score_card(title: str, score: float, delta: float | None = None) -> None:
    """Render an ATS score card with optional delta text."""
    delta_html = ""
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        delta_html = f"<div class='score-delta'>{sign}{delta:.1f} pts</div>"

    st.markdown(
        f"""
        <div class="score-card">
            <div class="score-title">{title}</div>
            <div class="score-number" style="color: {score_color(score)};">{score:.1f}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tags(keywords: list[str], color_class: str) -> None:
    """Render keyword tags for the match analysis section."""
    if not keywords:
        st.caption("None")
        return

    tag_html = " ".join(
        f"<span class='keyword-tag {color_class}'>{keyword}</span>" for keyword in keywords
    )
    st.markdown(tag_html, unsafe_allow_html=True)


def build_user_info(
    name: str,
    email: str,
    phone: str,
    headline: str = "",
    location: str = "",
    linkedin: str = "",
    portfolio: str = "",
    availability: str = "",
    work_mode: str = "",
) -> dict[str, str]:
    """Build a normalized user info dictionary."""
    return {
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "headline": headline.strip(),
        "location": location.strip(),
        "linkedin": linkedin.strip(),
        "portfolio": portfolio.strip(),
        "website": portfolio.strip(),
        "availability": availability.strip(),
        "work_mode": work_mode.strip(),
    }


def validate_inputs(
    uploaded_file: Any,
    job_description: str,
) -> bool:
    """Validate form inputs and report friendly Streamlit errors."""
    if uploaded_file is None:
        st.error("Please upload a PDF resume before generating materials.")
        return False

    if not job_description.strip():
        st.error("Please paste a job description before generating materials.")
        return False

    if job_description.strip() and len(job_description.strip()) < 500:
        st.error("Please paste a job description with at least 500 characters.")
        return False

    return True


def _is_fatal_validation_error(error: str) -> bool:
    """Only structural or truth-critical failures block delivery.

    Invented employers/metrics/emails mean the output cannot be trusted;
    broken LaTeX means it cannot be compiled. Everything else (residual
    wording, word counts) is surfaced as a warning with the output.
    """
    fatal_markers = (
        "invented or unsupported employer",
        "unsupported metric",
        "email not present in resume",
        "retired email used",
        "official title altered",
    )
    return any(marker in error for marker in fatal_markers)


def run_generation_pipeline(
    uploaded_file: Any,
    job_description: str,
    model_name: str,
    user_info: dict[str, str],
) -> dict[str, Any] | None:
    """Run extraction, scoring, LLM generation, rendering, and PDF creation."""
    base_resume_text = extract_text_from_pdf(uploaded_file) if uploaded_file else ""
    if not base_resume_text:
        st.error("Resume extraction failed. Please try another text-based PDF.")
        return None

    before_score = calculate_ats_score(base_resume_text, job_description)
    job_keywords = extract_keywords(job_description)

    try:
        start_time = time.perf_counter()
        pipeline_result = run_pipeline(
            uploaded_resume_pdf=None,
            resume_text=base_resume_text,
            job_description=job_description,
            overrides=user_info,
            logistics=user_info,
            questions_text="",
            requested_mode="streamlit_default",
            model_name=model_name,
        )
        elapsed_seconds = time.perf_counter() - start_time
    except Exception as exc:
        st.error(f"The v5 generation pipeline could not complete. Details: {exc}")
        return None

    tailored_resume = pipeline_result.resume_text
    cover_letter = pipeline_result.cover_letter_text
    if not tailored_resume:
        st.error("The resume generator returned an empty result. Please try again with a job description.")
        return None

    fatal_errors = [error for error in pipeline_result.validation_errors if _is_fatal_validation_error(error)]
    if fatal_errors:
        st.error("Quality gates blocked the output:\n\n" + "\n".join(fatal_errors[:8]))
        return None
    if pipeline_result.validation_errors:
        st.warning(
            "Review these before sending (the output is still usable):\n\n"
            + "\n".join(f"- {error}" for error in pipeline_result.validation_errors[:8])
        )

    after_score = calculate_ats_score(tailored_resume, job_description)
    comparison = compare_scores(before_score, after_score)
    keyword_analysis = generate_resume_keywords_analysis(
        base_resume_text=base_resume_text,
        tailored_resume=tailored_resume,
        job_keywords=job_keywords,
    )
    resume_latex = pipeline_result.resume_latex
    cover_letter_latex = pipeline_result.cover_letter_latex
    resolved_contact = pipeline_result.parsed_input.contacts
    resolved_user_info = {
        "name": resolved_contact.name,
        "email": resolved_contact.email,
        "phone": resolved_contact.phone,
        "headline": pipeline_result.resume_plan.headline if pipeline_result.resume_plan else "",
        "location": resolved_contact.location,
        "linkedin": resolved_contact.linkedin,
        "portfolio": resolved_contact.website,
        "website": resolved_contact.website,
    }
    resume_pdf = generate_resume_pdf(tailored_resume, resolved_user_info)
    cover_letter_pdf = generate_cover_letter_pdf(cover_letter, resolved_user_info) if cover_letter else b""

    return {
        "base_resume_text": base_resume_text,
        "tailored_resume": tailored_resume,
        "cover_letter": cover_letter,
        "before_score": before_score,
        "after_score": after_score,
        "comparison": comparison,
        "keyword_analysis": keyword_analysis,
        "resume_latex": resume_latex,
        "cover_letter_latex": cover_letter_latex,
        "resume_pdf": resume_pdf,
        "cover_letter_pdf": cover_letter_pdf,
        "answers_text": pipeline_result.answers_text,
        "mode_outputs": pipeline_result.mode_outputs,
        "jd_profile": pipeline_result.jd_profile,
        "model_name": model_name,
        "llm_used": bool(pipeline_result.metadata.get("llm_available")),
        "elapsed_seconds": elapsed_seconds,
    }


def render_generated_outputs(generated: dict[str, Any]) -> None:
    """Render scores, downloads, LaTeX text areas, previews, and analysis."""
    before = generated["before_score"]
    after = generated["after_score"]
    comparison = generated["comparison"]

    elapsed = generated.get("elapsed_seconds")
    timing_suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    if generated.get("llm_used"):
        st.success(f"Generated with local model `{generated['model_name']}` for higher-quality tailoring.{timing_suffix}")
    else:
        st.warning(
            "Ollama was not reachable, so this was generated with the deterministic fallback only. "
            "Start Ollama (`ollama serve`) and pull the selected model, then regenerate for stronger writing."
        )

    left, right = st.columns(2)
    with left:
        render_score_card("Before ATS Score", before["score"])
    with right:
        render_score_card("After ATS Score", after["score"], comparison["improvement"])

    row_one_left, row_one_right = st.columns(2)
    with row_one_left:
        st.download_button(
            "⬇ Download Resume PDF",
            data=generated["resume_pdf"],
            file_name="tailored_resume.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with row_one_right:
        if generated.get("cover_letter_pdf"):
            st.download_button(
                "⬇ Download Cover Letter PDF",
                data=generated["cover_letter_pdf"],
                file_name="cover_letter.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("⬇ Download Cover Letter PDF", disabled=True, use_container_width=True)

    row_two_left, row_two_right = st.columns(2)
    with row_two_left:
        if st.button("📋 Copy Resume LaTeX", use_container_width=True):
            st.session_state.show_resume_latex = True
    with row_two_right:
        if st.button("📋 Copy Cover Letter LaTeX", use_container_width=True, disabled=not generated.get("cover_letter_latex")):
            st.session_state.show_cover_latex = True

    if st.session_state.show_resume_latex:
        st.text_area(
            "Resume LaTeX",
            value=generated["resume_latex"],
            height=360,
            help="Select the contents and copy them to your clipboard.",
        )

    if st.session_state.show_cover_latex:
        st.text_area(
            "Cover Letter LaTeX",
            value=generated["cover_letter_latex"],
            height=360,
            help="Select the contents and copy them to your clipboard.",
        )

    with st.expander("Preview Tailored Resume", expanded=True):
        st.text(generated["tailored_resume"])

    with st.expander("Preview Cover Letter"):
        st.text(generated.get("cover_letter") or "No cover letter generated for this mode.")

    if generated.get("answers_text"):
        with st.expander("Application Answers", expanded=True):
            st.text(generated["answers_text"])

    analysis = generated["keyword_analysis"]
    with st.expander("Match Analysis", expanded=True):
        st.subheader("Matched keywords")
        render_tags(analysis["matched_original"], "tag-green")
        st.subheader("Missing keywords in original")
        render_tags(before["missing_keywords"], "tag-red")
        st.subheader("Keywords added by the AI")
        render_tags(analysis["added_by_ai"], "tag-blue")


def render_intro() -> None:
    """Render the pre-generation instructions and feature preview."""
    st.markdown(
        """
        Start by uploading a text-based PDF resume, then paste a full job description in the sidebar.
        The app extracts your resume text, scores it against the role, asks your local Ollama model to
        tailor truthful content, and returns a resume, cover letter, PDFs, LaTeX, and keyword analysis.
        """
    )

    c1, c2, c3 = st.columns(3)
    c1.info("Before and after ATS keyword scoring")
    c2.info("Local LLM generation through Ollama")
    c3.info("PDF downloads plus copyable LaTeX")


def inject_styles() -> None:
    """Inject small UI styles for cards and keyword tags."""
    st.markdown(
        """
        <style>
        .score-card {
            border: 1px solid #d0d5dd;
            border-radius: 8px;
            padding: 1rem;
            background: #ffffff;
        }
        .score-title {
            color: #475467;
            font-size: 0.95rem;
            margin-bottom: 0.35rem;
        }
        .score-number {
            font-size: 2.6rem;
            font-weight: 700;
            line-height: 1;
        }
        .score-delta {
            color: #027a48;
            font-size: 0.95rem;
            margin-top: 0.4rem;
        }
        .keyword-tag {
            border-radius: 999px;
            display: inline-block;
            font-size: 0.85rem;
            margin: 0.15rem 0.2rem 0.15rem 0;
            padding: 0.22rem 0.55rem;
        }
        .tag-green {
            background: #dcfae6;
            color: #05603a;
        }
        .tag-red {
            background: #fee4e2;
            color: #912018;
        }
        .tag-blue {
            background: #d1e9ff;
            color: #1849a9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(page_title="Resume Tailor AI", page_icon="📄", layout="wide")
    initialize_state()
    inject_styles()

    st.title("📄 Resume Tailor AI")
    st.caption("Upload your resume, paste a job description, get ATS-optimized materials")

    with st.sidebar:
        st.header("Inputs")
        uploaded_file = st.file_uploader("Resume PDF", type=["pdf"])
        job_description = st.text_area("Job Description", height=260)
        model_name = st.selectbox("LLM Model", MODEL_OPTIONS, index=0)
        if test_ollama_connection():
            st.caption("🟢 Ollama is reachable.")
        else:
            st.caption("🔴 Ollama is not reachable. Generation will use the deterministic fallback only.")
        force_fresh = st.checkbox(
            "Force fresh generation (ignore cache)",
            value=False,
            help="Identical resume + JD + model combinations are cached for instant re-generation. "
            "Check this to bypass the cache and get new model output.",
        )
        generate = st.button("Generate Tailored Materials", type="primary", use_container_width=True)

    if generate:
        os.environ["ATS_NINJA_LLM_CACHE"] = "0" if force_fresh else "1"
        user_info = build_user_info("", "", "")
        if validate_inputs(uploaded_file, job_description):
            with st.spinner("Analyzing resume and generating tailored materials..."):
                generated = run_generation_pipeline(
                    uploaded_file=uploaded_file,
                    job_description=job_description.strip(),
                    model_name=model_name,
                    user_info=user_info,
                )
            if generated:
                st.session_state.generated = generated
                st.session_state.show_resume_latex = False
                st.session_state.show_cover_latex = False

    if st.session_state.generated:
        render_generated_outputs(st.session_state.generated)
    else:
        render_intro()


if __name__ == "__main__":
    main()
