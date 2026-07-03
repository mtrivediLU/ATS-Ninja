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


COVER_LETTER_PROMPT = """
You are a professional career writer.

Write a confident, professional cover letter under 350 words. Reference specific
experiences from the tailored resume, match the tone and requirements from the job
description, and keep every claim grounded in the resume.

Structure:
1. Header with the user's name, email, and phone.
2. Opening paragraph: who the candidate is and what role they are targeting.
3. One or two body paragraphs: relevant experience from the tailored resume.
4. Closing paragraph: concise call to action.

User Info:
Name: {name}
Email: {email}
Phone: {phone}

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
        input_variables=["name", "email", "phone", "tailored_resume", "job_description"],
        template=COVER_LETTER_PROMPT,
    )
    variables = {
        "name": (user_info or {}).get("name", "Your Name"),
        "email": (user_info or {}).get("email", "your.email@example.com"),
        "phone": (user_info or {}).get("phone", "Your Phone"),
        "tailored_resume": tailored_resume.strip(),
        "job_description": job_description.strip(),
    }
    result = _invoke_prompt(llm, prompt, variables)

    return _extract_chain_text(result)


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
