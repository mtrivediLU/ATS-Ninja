from __future__ import annotations

from core.models import AnswerPlan


def generate_answers_text(plan: AnswerPlan) -> str:
    """Produce Mode Q application answers in paste-ready plain text."""
    lines: list[str] = []
    for index, (question, answer) in enumerate(zip(plan.questions, plan.answers, strict=False), start=1):
        lines.append(f"**Q{index}: {question.strip()}**")
        lines.append(answer.strip())
        lines.append("")
    if plan.placeholders:
        lines.append("Placeholders used: " + ", ".join(plan.placeholders))
    return "\n".join(lines).strip()
