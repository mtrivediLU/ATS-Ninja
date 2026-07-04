from __future__ import annotations

import re

from core.models import Profile


PRODUCTION_WORDS = {"production", "owned", "built", "shipped", "launched", "deployed"}
UNSUPPORTED_SCALE_WORDS = {"uptime", "users", "revenue", "millions", "billion", "latency"}


def validate_claims(text: str, profile: Profile) -> list[str]:
    """Validate generated claims against v5 profile constraints."""
    errors: list[str] = []
    lowered = text.lower()

    for email in profile.retired_emails:
        if email.lower() in lowered:
            errors.append("retired email used")
    if re.search(r"[\w.+-]+@laurentian\.ca", lowered):
        errors.append("Laurentian email used")

    experience_text = _section_between(text, "Professional Experience", "Education")
    for term in profile.tier_c:
        if re.search(rf"(?<![\w+#.-]){re.escape(term)}(?![\w+#.-])", experience_text.lower()):
            errors.append(f"Tier C term in experience bullets: {profile.tier_c[term]}")

    experience_lowered = experience_text.lower()
    for term in list(profile.tier_b) + list(profile.tier_c):
        if term in experience_lowered and _near_production_claim(experience_lowered, term):
            errors.append(f"unsupported production ownership claim for {term}")

    for word in UNSUPPORTED_SCALE_WORDS:
        if word in lowered and not any(metric.lower() in lowered for metric in profile.supported_metrics):
            errors.append(f"unsupported scale claim: {word}")

    metric_like = re.findall(r"\b\d+(?:\.\d+)?%|\b\d+\+?\s+(?:users|customers|million|billion|hours|platforms)", text, flags=re.IGNORECASE)
    for metric in metric_like:
        if not any(metric.lower() in supported.lower() for supported in profile.supported_metrics):
            errors.append(f"unsupported metric: {metric}")

    if "\\resumeSubheading" in text or "Professional Experience" in text:
        errors.extend(_validate_official_titles(text, profile))
        errors.extend(_validate_known_companies(text, profile))
    return _dedupe(errors)


def _near_production_claim(text: str, term: str) -> bool:
    pattern = rf"(?:{'|'.join(PRODUCTION_WORDS)}).{{0,60}}{re.escape(term)}|{re.escape(term)}.{{0,60}}(?:{'|'.join(PRODUCTION_WORDS)})"
    return bool(re.search(pattern, text))


def _validate_official_titles(text: str, profile: Profile) -> list[str]:
    errors: list[str] = []
    comparable = _latex_unescape(text)
    for experience in profile.experiences:
        if experience.company in comparable:
            company_index = comparable.find(experience.company)
            block = comparable[company_index:company_index + 320]
            if experience.title not in block:
                errors.append(f"official title altered for {experience.company}")
    return errors


def _validate_known_companies(text: str, profile: Profile) -> list[str]:
    errors: list[str] = []
    allowed = {company.lower() for company in profile.allowed_companies}
    experience_text = _section_between(text, "Professional Experience", "Education") or text
    for match in re.finditer(r"\\resumeSubheading\s*\{([^}]+)\}", experience_text):
        company = re.sub(r"\\href\{[^}]+\}\{([^}]+)\}", r"\1", match.group(1)).strip().lower()
        company = _latex_unescape(company)
        if company and company not in allowed:
            errors.append(f"invented or unsupported employer: {company}")
    return errors


def _section_between(text: str, start: str, end: str) -> str:
    pattern = rf"{re.escape(start)}(.*?){re.escape(end)}"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _latex_unescape(text: str) -> str:
    return (
        text.replace(r"\&", "&")
        .replace(r"\%", "%")
        .replace(r"\$", "$")
        .replace(r"\#", "#")
        .replace(r"\_", "_")
    )
