from __future__ import annotations

from core.latex_renderer import cover_letter_to_latex
from core.models import CoverLetterPlan


def generate_cover_letter_text(plan: CoverLetterPlan) -> str:
    """Render cover-letter body text from a structured plan."""
    return _strip_banned_dashes("\n\n".join(plan.body_paragraphs).strip())


def generate_cover_letter_latex(plan: CoverLetterPlan) -> str:
    """Produce a complete standalone Overleaf-ready cover letter."""
    contact = plan.contacts
    user_info = {
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "headline": "",
        "location": contact.location,
        "linkedin": contact.linkedin,
        "portfolio": contact.website,
    }
    return _strip_banned_dashes(
        cover_letter_to_latex(generate_cover_letter_text(plan), user_info)
    ).strip()


def format_cover_letter_output(plan: CoverLetterPlan, latex_code: str) -> str:
    """Format Mode C output exactly."""
    return (
        f"**Letter angle:** {plan.angle}\n"
        f"**Word count:** {plan.word_count}\n"
        "```latex\n"
        f"{latex_code.strip()}\n"
        "```"
    )


def _strip_banned_dashes(text: str) -> str:
    return text.replace("—", ",").replace("–", " to ").replace("--", "-")
