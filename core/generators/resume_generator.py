from __future__ import annotations

from core.latex_renderer import resume_to_latex
from core.models import ResumePlan
from core.output_repair import soften_banned_style


def generate_resume_text(plan: ResumePlan) -> str:
    """Render the structured resume plan into parseable resume text."""
    contact = plan.contacts
    lines: list[str] = [
        "Candidate Header",
        f"Professional Headline: {plan.headline}",
        f"Location: {contact.location}",
        f"LinkedIn: {contact.linkedin}",
        f"Portfolio: {contact.website}",
        f"Work Authorization: {contact.work_authorization}",
        f"Relocation: {contact.relocation}",
        "",
        "Professional Summary",
        plan.summary,
        "",
        "Technical Skills",
    ]
    for category, items in plan.skill_groups:
        lines.append(f"{category}: {', '.join(items)}")

    lines.extend(["", "Professional Experience"])
    for entry in plan.experience:
        lines.append(
            f"Company: {entry.company} | Location: {entry.location} | Title: {entry.title} | Dates: {entry.dates}"
        )
        for bullet in entry.bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("Education")
    for entry in plan.education:
        lines.append(
            f"Institution: {entry.institution} | Location: {entry.location} | Degree: {entry.degree} | Dates: {entry.dates}"
        )
        for bullet in entry.bullets:
            lines.append(f"- {bullet}")
    lines.extend(["", "Certifications"])
    for cert in plan.certifications:
        parts = [cert.name]
        if cert.date:
            parts.append(cert.date)
        if cert.link:
            parts.append(cert.link)
        lines.append("- " + " | ".join(parts))
    return soften_banned_style(_strip_banned_dashes("\n".join(lines).strip()))


def generate_resume_latex(plan: ResumePlan) -> str:
    """Produce a complete Overleaf-ready LaTeX resume."""
    user_info = _user_info(plan)
    return _strip_banned_dashes(resume_to_latex(generate_resume_text(plan), user_info)).strip()


def format_resume_output(plan: ResumePlan, latex_code: str) -> str:
    """Format Mode R output exactly."""
    role = f"{plan.jd_profile.title} at {plan.jd_profile.company}"
    analysis = "\n".join(plan.analysis[:4])
    return (
        f"**Role:** {role}\n"
        f"**Interview Call Probability:** {plan.interview_probability}%\n"
        f"**Analysis:** {analysis}\n"
        "```latex\n"
        f"{latex_code.strip()}\n"
        "```"
    )


def _user_info(plan: ResumePlan) -> dict[str, str]:
    contact = plan.contacts
    return {
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "headline": plan.headline,
        "location": contact.location,
        "linkedin": contact.linkedin,
        "portfolio": contact.website,
        "work_authorization": contact.work_authorization,
        "relocation": contact.relocation,
    }


def _strip_banned_dashes(text: str) -> str:
    return text.replace("—", ",").replace("–", " to ").replace("--", "-")
