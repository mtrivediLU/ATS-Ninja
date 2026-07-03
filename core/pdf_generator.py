from __future__ import annotations

import html
import re
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.latex_renderer import build_cover_letter_context, build_resume_context


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "templates"
PRIMARY_COLOR = colors.HexColor("#003366")
ACCENT_COLOR = colors.HexColor("#0070C0")
TEXT_COLOR = colors.HexColor("#111111")
MUTED_COLOR = colors.HexColor("#3F4652")


def latex_to_pdf(latex_code: str, output_path: str) -> bytes:
    """Convert simple LaTeX code into PDF bytes, with ReportLab fallback."""
    text = _simple_latex_to_text(latex_code or "")
    html_content = _text_to_html(text)

    try:
        pdf_bytes = _weasyprint_pdf(html_content)
    except Exception:
        pdf_bytes = _reportlab_text_pdf(text, title="Document")

    if output_path:
        Path(output_path).write_bytes(pdf_bytes)
    return pdf_bytes


def generate_resume_pdf(resume_text: str, user_info: dict[str, str]) -> bytes:
    """Generate a polished downloadable resume PDF."""
    context = build_resume_context(resume_text or "", user_info)

    try:
        html_content = _render_template("resume_template.html", context)
        return _weasyprint_pdf(html_content)
    except Exception:
        return _reportlab_resume_pdf(context)


def generate_cover_letter_pdf(cover_letter_text: str, user_info: dict[str, str]) -> bytes:
    """Generate a polished downloadable cover letter PDF."""
    context = build_cover_letter_context(cover_letter_text or "", user_info)

    try:
        html_content = _render_template("cover_letter_template.html", context)
        return _weasyprint_pdf(html_content)
    except Exception:
        return _reportlab_cover_letter_pdf(context)


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


def _reportlab_resume_pdf(context: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title=context.get("name", "Resume"),
    )
    styles = _styles()
    story: list[Any] = []

    story.extend(_header_flowables(context, styles, compact=True))
    story.extend(_section_heading("Professional Summary", styles))
    if context.get("summary"):
        story.append(Paragraph(_escape(context["summary"]), styles["BodyTight"]))

    if context.get("skills"):
        story.extend(_section_heading("Technical Skills", styles))
        for group in context["skills"]:
            story.append(
                Paragraph(
                    f"<b>{_escape(group.get('category', 'Skills'))}:</b> "
                    f"{_escape(group.get('items_text', ''))}",
                    styles["BodyTight"],
                )
            )

    if context.get("experience"):
        story.extend(_section_heading("Professional Experience", styles))
        for entry in context["experience"]:
            story.extend(_entry_flowables(entry, styles, document.width, "company", "title"))

    if context.get("education"):
        story.extend(_section_heading("Education", styles))
        for entry in context["education"]:
            story.extend(_entry_flowables(entry, styles, document.width, "institution", "degree"))

    if context.get("certifications"):
        story.extend(_section_heading("Certifications", styles))
        for item in context["certifications"]:
            left = f"<b>{_escape(item.get('name', ''))}</b>"
            if item.get("issuer"):
                left += f", {_escape(item['issuer'])}"
            if item.get("link"):
                left += f" <font color='#0070C0'>{_escape(item.get('link_label', 'Verify'))}</font>"
            right = _escape(item.get("date", ""))
            story.append(_two_column_row(left, right, styles, document.width, "BodyTight"))

    document.build(story)
    return buffer.getvalue()


def _reportlab_cover_letter_pdf(context: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title=f"{context.get('name', 'Candidate')} Cover Letter",
    )
    styles = _styles()
    story: list[Any] = []

    story.extend(_header_flowables(context, styles, compact=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph(_escape(context.get("date", "")), styles["Body"]))
    story.append(Spacer(1, 8))

    for paragraph in context.get("body", []):
        story.append(Paragraph(_escape(paragraph), styles["LetterBody"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Sincerely,<br/>{_escape(context.get('name', ''))}", styles["Body"]))

    document.build(story)
    return buffer.getvalue()


def _header_flowables(context: dict[str, Any], styles: dict[str, ParagraphStyle], compact: bool) -> list[Any]:
    flowables: list[Any] = [
        Paragraph(_escape(context.get("name", "Your Name")), styles["Name"]),
    ]
    if context.get("headline"):
        flowables.append(Paragraph(_escape(context["headline"]), styles["Headline"]))

    for row in context.get("contact_rows", []):
        labels = [item.get("label", "") for item in row if item.get("label")]
        if labels:
            flowables.append(Paragraph(_escape(" | ".join(labels)), styles["Contact"]))

    flowables.append(Spacer(1, 3 if compact else 8))
    flowables.append(HRFlowable(width="100%", thickness=1.2, color=PRIMARY_COLOR, spaceAfter=6))
    return flowables


def _section_heading(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Spacer(1, 5),
        Paragraph(_escape(text.upper()), styles["Section"]),
        HRFlowable(width="100%", thickness=1.0, color=PRIMARY_COLOR, spaceBefore=0, spaceAfter=4),
    ]


def _entry_flowables(
    entry: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    width: float,
    primary_key: str,
    secondary_key: str,
) -> list[Any]:
    flowables: list[Any] = []
    flowables.append(
        _two_column_row(
            f"<b>{_escape(entry.get(primary_key, ''))}</b>",
            f"<b>{_escape(entry.get('location', ''))}</b>",
            styles,
            width,
            "EntryPrimary",
        )
    )
    flowables.append(
        _two_column_row(
            f"<i>{_escape(entry.get(secondary_key, ''))}</i>",
            f"<i>{_escape(entry.get('dates', ''))}</i>",
            styles,
            width,
            "EntrySecondary",
        )
    )
    for bullet in entry.get("bullets", []):
        flowables.append(Paragraph(f"&bull; {_escape(bullet)}", styles["Bullet"]))
    flowables.append(Spacer(1, 3))
    return flowables


def _two_column_row(
    left: str,
    right: str,
    styles: dict[str, ParagraphStyle],
    width: float,
    style_name: str,
) -> Table:
    table = Table(
        [[Paragraph(left, styles[style_name]), Paragraph(right, styles[style_name + "Right"])]],
        colWidths=[width * 0.72, width * 0.28],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Name": ParagraphStyle(
            "Name",
            parent=base["Title"],
            alignment=1,
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=26,
            textColor=PRIMARY_COLOR,
            spaceAfter=3,
        ),
        "Headline": ParagraphStyle(
            "Headline",
            parent=base["BodyText"],
            alignment=1,
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=TEXT_COLOR,
            spaceAfter=3,
        ),
        "Contact": ParagraphStyle(
            "Contact",
            parent=base["BodyText"],
            alignment=1,
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=MUTED_COLOR,
            spaceAfter=1,
        ),
        "Section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=14,
            textColor=PRIMARY_COLOR,
            spaceAfter=0,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=TEXT_COLOR,
            spaceAfter=7,
        ),
        "BodyTight": ParagraphStyle(
            "BodyTight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.8,
            leading=12.3,
            textColor=TEXT_COLOR,
            spaceAfter=2,
        ),
        "LetterBody": ParagraphStyle(
            "LetterBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=TEXT_COLOR,
            spaceAfter=10,
        ),
        "EntryPrimary": ParagraphStyle(
            "EntryPrimary",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            textColor=TEXT_COLOR,
        ),
        "EntryPrimaryRight": ParagraphStyle(
            "EntryPrimaryRight",
            parent=base["BodyText"],
            alignment=2,
            fontName="Helvetica",
            fontSize=9.4,
            leading=12,
            textColor=TEXT_COLOR,
        ),
        "EntrySecondary": ParagraphStyle(
            "EntrySecondary",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9.4,
            leading=11,
            textColor=TEXT_COLOR,
        ),
        "EntrySecondaryRight": ParagraphStyle(
            "EntrySecondaryRight",
            parent=base["BodyText"],
            alignment=2,
            fontName="Helvetica-Oblique",
            fontSize=9.4,
            leading=11,
            textColor=TEXT_COLOR,
        ),
        "BodyTightRight": ParagraphStyle(
            "BodyTightRight",
            parent=base["BodyText"],
            alignment=2,
            fontName="Helvetica-Oblique",
            fontSize=9.4,
            leading=12,
            textColor=MUTED_COLOR,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=12,
            leftIndent=9,
            firstLineIndent=-7,
            textColor=TEXT_COLOR,
            spaceAfter=1,
        ),
    }


def _reportlab_text_pdf(text: str, title: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title,
    )
    styles = _styles()
    story: list[Any] = []
    for line in [line.rstrip() for line in (text or "No content generated.").splitlines()]:
        clean = _escape(line.strip())
        if not clean:
            story.append(Spacer(1, 4))
            continue
        style = styles["Section"] if clean.isupper() else styles["Body"]
        story.append(Paragraph(clean, style))

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


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=False)
