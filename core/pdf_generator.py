from __future__ import annotations

import html
import re
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO
from io import StringIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from core.latex_renderer import parse_resume_sections, split_cover_letter_paragraphs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "templates"


def latex_to_pdf(latex_code: str, output_path: str) -> bytes:
    """Convert simple LaTeX code into PDF bytes, with ReportLab fallback."""
    text = _simple_latex_to_text(latex_code or "")
    html_content = _text_to_html(text)

    try:
        pdf_bytes = _weasyprint_pdf(html_content)
    except Exception:
        pdf_bytes = _reportlab_pdf_from_text(text, title="Document")

    if output_path:
        Path(output_path).write_bytes(pdf_bytes)
    return pdf_bytes


def generate_resume_pdf(resume_text: str, user_info: dict[str, str]) -> bytes:
    """Generate a downloadable resume PDF from structured resume text."""
    sections = parse_resume_sections(resume_text or "")
    context = {
        "name": _user_value(user_info, "name", "Your Name"),
        "email": _user_value(user_info, "email", "your.email@example.com"),
        "phone": _user_value(user_info, "phone", "Your Phone"),
        **sections,
    }

    try:
        html_content = _render_template("resume_template.html", context)
        return _weasyprint_pdf(html_content)
    except Exception:
        return _reportlab_pdf_from_text(resume_text or "", title=context["name"])


def generate_cover_letter_pdf(cover_letter_text: str, user_info: dict[str, str]) -> bytes:
    """Generate a downloadable cover letter PDF from cover letter text."""
    from datetime import date

    context = {
        "name": _user_value(user_info, "name", "Your Name"),
        "email": _user_value(user_info, "email", "your.email@example.com"),
        "phone": _user_value(user_info, "phone", "Your Phone"),
        "date": _format_date(date.today()),
        "body": split_cover_letter_paragraphs(cover_letter_text or "", user_info),
    }

    try:
        html_content = _render_template("cover_letter_template.html", context)
        return _weasyprint_pdf(html_content)
    except Exception:
        return _reportlab_pdf_from_text(cover_letter_text or "", title=f"{context['name']} Cover Letter")


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html",), default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template(template_name)
    return template.render(**context)


def _weasyprint_pdf(html_content: str) -> bytes:
    output = StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        from weasyprint import HTML

        return HTML(string=html_content).write_pdf()


def _reportlab_pdf_from_text(text: str, title: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title,
    )
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.black,
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=5,
    )

    story: list[Any] = []
    lines = [line.rstrip() for line in (text or "No content generated.").splitlines()]
    for line in lines:
        clean = html.escape(line.strip())
        if not clean:
            story.append(Spacer(1, 4))
            continue
        is_heading = clean.isupper() or clean.lower() in {
            "professional summary",
            "core skills",
            "professional experience",
            "education",
            "certifications",
        }
        style = heading_style if is_heading else body_style
        prefix = "• " if line.lstrip().startswith(("-", "*", "•")) else ""
        story.append(Paragraph(f"{prefix}{clean.lstrip('-*• ').strip()}", style))

    document.build(story)
    return buffer.getvalue()


def _simple_latex_to_text(latex_code: str) -> str:
    text = re.sub(r"\\(?:documentclass|usepackage)(?:\[[^\]]*\])?\{[^}]*\}", "", latex_code)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}", "", text)
    text = re.sub(r"\\(?:section\*?|subsection\*?)\{([^}]*)\}", r"\1\n", text)
    text = re.sub(r"\\(?:textbf|href)\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\item\s*", "- ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", text)
    text = text.replace(r"\&", "&").replace(r"\%", "%").replace(r"\$", "$")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _text_to_html(text: str) -> str:
    paragraphs = "".join(f"<p>{html.escape(line)}</p>" for line in text.splitlines() if line.strip())
    return f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.45; color: #111; }}
          p {{ margin: 0 0 8px; }}
        </style>
      </head>
      <body>{paragraphs}</body>
    </html>
    """


def _user_value(user_info: dict[str, str] | None, key: str, default: str) -> str:
    value = (user_info or {}).get(key, default)
    return str(value or default).strip()


def _format_date(value: Any) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"
