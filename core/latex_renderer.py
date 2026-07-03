from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "templates"


SECTION_ALIASES = {
    "professional summary": "summary",
    "summary": "summary",
    "profile": "summary",
    "core skills": "skills",
    "skills": "skills",
    "technical skills": "skills",
    "professional experience": "experience",
    "experience": "experience",
    "work experience": "experience",
    "employment history": "experience",
    "education": "education",
    "certifications": "certifications",
    "certification": "certifications",
    "licenses": "certifications",
}


def resume_to_latex(resume_text: str, user_info: dict[str, str]) -> str:
    """Render structured resume text into a complete LaTeX document."""
    sections = parse_resume_sections(resume_text or "")
    environment = _template_environment()
    template = environment.get_template("resume_template.tex")

    return template.render(
        name=latex_escape(_user_value(user_info, "name", "Your Name")),
        email=latex_escape(_user_value(user_info, "email", "your.email@example.com")),
        phone=latex_escape(_user_value(user_info, "phone", "Your Phone")),
        summary=latex_escape(sections["summary"]),
        skills=[latex_escape(item) for item in sections["skills"]],
        experience=[latex_escape(item) for item in sections["experience"]],
        education=[latex_escape(item) for item in sections["education"]],
        certifications=[latex_escape(item) for item in sections["certifications"]],
    )


def cover_letter_to_latex(cover_letter_text: str, user_info: dict[str, str]) -> str:
    """Render cover letter text into a complete LaTeX document."""
    from datetime import date

    environment = _template_environment()
    template = environment.get_template("cover_letter_template.tex")

    return template.render(
        name=latex_escape(_user_value(user_info, "name", "Your Name")),
        email=latex_escape(_user_value(user_info, "email", "your.email@example.com")),
        phone=latex_escape(_user_value(user_info, "phone", "Your Phone")),
        date=latex_escape(_format_date(date.today())),
        body=[
            latex_escape(paragraph)
            for paragraph in split_cover_letter_paragraphs(cover_letter_text, user_info)
        ],
    )


def parse_resume_sections(resume_text: str) -> dict[str, Any]:
    """Parse a structured resume into summary, skills, experience, education, and certifications."""
    sections: dict[str, Any] = {
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
    }
    if not resume_text or not resume_text.strip():
        return sections

    current_section = "summary"
    buffers: dict[str, list[str]] = {key: [] for key in sections}

    for raw_line in resume_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        normalized_heading = _normalize_heading(line)
        if normalized_heading in SECTION_ALIASES:
            current_section = SECTION_ALIASES[normalized_heading]
            continue

        if current_section == "skills":
            buffers[current_section].extend(_split_skills_line(line))
        else:
            buffers[current_section].append(_clean_content_line(line))

    sections["summary"] = " ".join(buffers["summary"]).strip()
    sections["skills"] = _dedupe([item for item in buffers["skills"] if item])
    sections["experience"] = [item for item in buffers["experience"] if item]
    sections["education"] = [item for item in buffers["education"] if item]
    sections["certifications"] = [item for item in buffers["certifications"] if item]

    return sections


def split_cover_letter_paragraphs(
    cover_letter_text: str,
    user_info: dict[str, str] | None = None,
) -> list[str]:
    """Split a cover letter into readable paragraphs."""
    text = _strip_cover_letter_header((cover_letter_text or "").strip(), user_info)
    if not text:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) == 1:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines if len(lines) > 1 else paragraphs
    return paragraphs


def latex_escape(value: str) -> str:
    """Escape text for safe inclusion in simple LaTeX templates."""
    if value is None:
        return ""

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def _template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(disabled_extensions=("tex",), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _user_value(user_info: dict[str, str] | None, key: str, default: str) -> str:
    value = (user_info or {}).get(key, default)
    return str(value or default).strip()


def _normalize_heading(line: str) -> str:
    heading = line.strip().strip(":").strip()
    heading = re.sub(r"^[#*\-\s]+", "", heading)
    heading = re.sub(r"[*_]+$", "", heading)
    heading = heading.strip().strip(":").lower()
    return re.sub(r"\s+", " ", heading)


def _clean_content_line(line: str) -> str:
    cleaned = re.sub(r"^[\-*•]\s*", "", line.strip())
    return cleaned.strip()


def _split_skills_line(line: str) -> list[str]:
    cleaned = _clean_content_line(line)
    parts = re.split(r"[,;|]|\s{2,}", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped


def _format_date(value: Any) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _strip_cover_letter_header(text: str, user_info: dict[str, str] | None) -> str:
    if not text or not user_info:
        return text

    name = _user_value(user_info, "name", "").lower()
    email = _user_value(user_info, "email", "").lower()
    phone = _user_value(user_info, "phone", "").lower()
    lines = text.splitlines()
    first_body_index = 0

    for index, line in enumerate(lines[:8]):
        normalized = line.strip().lower()
        if not normalized:
            first_body_index = index + 1
            continue
        is_header_line = (
            (name and name in normalized)
            or (email and email in normalized)
            or (phone and phone in normalized)
            or "@" in normalized
            or normalized.startswith("phone:")
            or normalized.startswith("email:")
        )
        if is_header_line:
            first_body_index = index + 1
            continue
        break

    return "\n".join(lines[first_body_index:]).strip()
