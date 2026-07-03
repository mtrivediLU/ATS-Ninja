from __future__ import annotations

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
You are an expert resume writer and ATS optimization specialist.

Read the base resume and the job description. Identify key skills, technologies, and
qualifications from the job description. Rewrite the resume to emphasize matching
experiences, add missing keywords naturally where the user has relevant experience, and
use clear quantified achievements where possible.

NEVER fabricate experience, jobs, or skills that are not in the original resume. Only rephrase, reorder, and emphasize existing content.

Format the output as a structured resume with these exact section headers:
Professional Summary
Core Skills
Professional Experience
Education
Certifications

Use bullet points for experience. Keep the resume truthful, concise, and ATS-friendly.

User Info:
Name: {name}
Email: {email}
Phone: {phone}

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
        input_variables=["name", "email", "phone", "base_resume_text", "job_description"],
        template=RESUME_PROMPT,
    )
    variables = {
        "name": (user_info or {}).get("name", "Your Name"),
        "email": (user_info or {}).get("email", "your.email@example.com"),
        "phone": (user_info or {}).get("phone", "Your Phone"),
        "base_resume_text": base_resume_text.strip(),
        "job_description": job_description.strip(),
    }
    result = _invoke_prompt(llm, prompt, variables)

    return _extract_chain_text(result)


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


def _invoke_prompt(llm: Any, prompt: PromptTemplate, variables: dict[str, str]) -> Any:
    if LLMChain is not None:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.invoke(variables)

    chain = prompt | llm
    return chain.invoke(variables)
