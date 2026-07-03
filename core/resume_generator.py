from __future__ import annotations

import re
from typing import Any

try:
    from langchain.chains import LLMChain
except ImportError:  # pragma: no cover - LangChain 1.x compatibility
    LLMChain = None  # type: ignore

try:
    from langchain.prompts import PromptTemplate
except ImportError:  # pragma: no cover - LangChain 1.x compatibility
    from langchain_core.prompts import PromptTemplate

from core.ats_scorer import keyword_in_text


RESUME_PROMPT = """
You are an elite technical resume strategist, ATS optimization specialist, and recruiter-facing
editor. Your output must read like a polished senior-candidate resume, not a generic rewrite.

Read the base resume and job description. Identify the role's strongest buying signals:
required skills, domain keywords, seniority, tools, business outcomes, and qualifications.
Rewrite the resume to foreground the most relevant truthful evidence from the base resume.
Use sharp, quantified bullets with this pattern when possible:
Action verb + scope/system/product + tool/domain + measurable business or technical outcome.

NEVER fabricate experience, jobs, or skills that are not in the original resume. Only rephrase, reorder, and emphasize existing content.

Quality rules:
- Keep the resume concise, dense, and recruiter-friendly.
- Prefer strong verbs: built, led, designed, shipped, automated, optimized, integrated, reduced.
- Add missing ATS keywords only when the original resume supports them.
- Do not keyword-stuff. Do not add unsupported certifications, employers, metrics, degrees, or tools.
- Prefer categorized skills over a flat skills dump.
- Prioritize the most relevant 4-6 roles/projects if the resume is long.
- Use no Markdown tables, no code fences, and no commentary.

Return exactly this parseable structure:

Candidate Header
Professional Headline: <targeted headline for this job, 6-12 words>
Location: <location if present in resume or user info, otherwise blank>
LinkedIn: <LinkedIn URL if present, otherwise blank>
Portfolio: <portfolio/site URL if present, otherwise blank>
Work Authorization: <work authorization if present, otherwise blank>
Relocation: <relocation note if present, otherwise blank>

Professional Summary
<3-4 sentence summary, 70-95 words, tailored to the job and grounded in the resume>

Technical Skills
<Category>: <comma-separated skills>
<Category>: <comma-separated skills>
<Category>: <comma-separated skills>

Professional Experience
Company: <company> | Location: <location> | Title: <title> | Dates: <dates>
- <impact bullet>
- <impact bullet>
- <impact bullet>

Company: <company> | Location: <location> | Title: <title> | Dates: <dates>
- <impact bullet>
- <impact bullet>

Education
Institution: <school> | Location: <location> | Degree: <degree> | Dates: <dates>
- <optional thesis, publication, honors, or relevant detail if present>

Certifications
- <certification name> | <year/date if present> | <verification URL if present>

User Info:
Name: {name}
Email: {email}
Phone: {phone}
Preferred Headline: {headline}
Location: {location}
LinkedIn: {linkedin}
Portfolio: {portfolio}

Base Resume:
{base_resume_text}

Job Description:
{job_description}

Tailored Resume:
"""


def generate_tailored_resume(
    base_resume_text: str,
    job_description: str,
    llm: Any,
    user_info: dict[str, str],
) -> str:
    """Generate a tailored resume from base resume text and a job description."""
    if not base_resume_text or not base_resume_text.strip():
        return ""
    if not job_description or not job_description.strip():
        return ""
    if llm is None:
        raise ValueError("An LLM instance is required to generate a tailored resume.")

    prompt = PromptTemplate(
        input_variables=[
            "name",
            "email",
            "phone",
            "headline",
            "location",
            "linkedin",
            "portfolio",
            "base_resume_text",
            "job_description",
        ],
        template=RESUME_PROMPT,
    )
    variables = {
        "name": (user_info or {}).get("name", "Your Name"),
        "email": (user_info or {}).get("email", "your.email@example.com"),
        "phone": (user_info or {}).get("phone", "Your Phone"),
        "headline": (user_info or {}).get("headline", ""),
        "location": (user_info or {}).get("location", ""),
        "linkedin": (user_info or {}).get("linkedin", ""),
        "portfolio": (user_info or {}).get("portfolio", ""),
        "base_resume_text": base_resume_text.strip(),
        "job_description": job_description.strip(),
    }
    result = _invoke_prompt(llm, prompt, variables)

    return _clean_generated_text(_extract_chain_text(result), label="Tailored Resume")


def generate_resume_keywords_analysis(
    base_resume_text: str,
    tailored_resume: str,
    job_keywords: list[str],
) -> dict[str, list[str]]:
    """Compare job keywords across the original and tailored resumes."""
    keywords = job_keywords or []
    matched_original = [keyword for keyword in keywords if keyword_in_text(base_resume_text or "", keyword)]
    added_by_ai = [
        keyword
        for keyword in keywords
        if not keyword_in_text(base_resume_text or "", keyword)
        and keyword_in_text(tailored_resume or "", keyword)
    ]
    still_missing = [
        keyword
        for keyword in keywords
        if not keyword_in_text(base_resume_text or "", keyword)
        and not keyword_in_text(tailored_resume or "", keyword)
    ]

    return {
        "matched_original": matched_original,
        "added_by_ai": added_by_ai,
        "still_missing": still_missing,
    }


def _extract_chain_text(result: Any) -> str:
    if isinstance(result, dict):
        value = result.get("text") or result.get("output_text") or result.get("content") or ""
        return str(value).strip()
    content = getattr(result, "content", None)
    if content is not None:
        return str(content).strip()
    return str(result or "").strip()


def _clean_generated_text(text: str, label: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:text|markdown|latex)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(rf"^\s*(?:{re.escape(label)}|Resume)\s*:?\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _invoke_prompt(llm: Any, prompt: PromptTemplate, variables: dict[str, str]) -> Any:
    if LLMChain is not None:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.invoke(variables)

    chain = prompt | llm
    return chain.invoke(variables)
