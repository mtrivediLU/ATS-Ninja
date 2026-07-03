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


COVER_LETTER_PROMPT = """
You are an elite career writer. Write a crisp, credible cover letter that sounds like a
strong candidate wrote it for this exact role, not a generic AI template.

Rules:
- Keep it under 330 words.
- Do not invent facts, metrics, companies, skills, or credentials.
- Reference 2-3 specific experiences from the tailored resume that directly match the job.
- Match the job description's priorities and tone.
- Avoid empty phrases like "I am writing to express my interest" and "dynamic team."
- Use confident, plain language.
- Return body text only. Do not include the name/contact header or date; the document
  template will add those.

Structure:
1. Salutation. Use "Dear Hiring Manager," unless a company, team, or recipient is obvious.
2. Opening paragraph: role fit and strongest value proposition.
3. One or two body paragraphs: specific evidence from the resume, tied to role requirements.
4. Closing paragraph: direct, professional call to action.

User Info:
Name: {name}
Email: {email}
Phone: {phone}
Professional Headline: {headline}
Location: {location}

Tailored Resume:
{tailored_resume}

Job Description:
{job_description}

Cover Letter:
"""


def generate_cover_letter(
    tailored_resume: str,
    job_description: str,
    llm: Any,
    user_info: dict[str, str],
) -> str:
    """Generate a concise cover letter from a tailored resume and job description."""
    if not tailored_resume or not tailored_resume.strip():
        return ""
    if not job_description or not job_description.strip():
        return ""
    if llm is None:
        raise ValueError("An LLM instance is required to generate a cover letter.")

    prompt = PromptTemplate(
        input_variables=[
            "name",
            "email",
            "phone",
            "headline",
            "location",
            "tailored_resume",
            "job_description",
        ],
        template=COVER_LETTER_PROMPT,
    )
    variables = {
        "name": (user_info or {}).get("name", "Your Name"),
        "email": (user_info or {}).get("email", "your.email@example.com"),
        "phone": (user_info or {}).get("phone", "Your Phone"),
        "headline": (user_info or {}).get("headline", ""),
        "location": (user_info or {}).get("location", ""),
        "tailored_resume": tailored_resume.strip(),
        "job_description": job_description.strip(),
    }
    result = _invoke_prompt(llm, prompt, variables)

    return _clean_generated_text(_extract_chain_text(result), label="Cover Letter")


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
    cleaned = re.sub(r"^```(?:text|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(rf"^\s*(?:{re.escape(label)}|Body)\s*:?\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _invoke_prompt(llm: Any, prompt: PromptTemplate, variables: dict[str, str]) -> Any:
    if LLMChain is not None:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.invoke(variables)

    chain = prompt | llm
    return chain.invoke(variables)
