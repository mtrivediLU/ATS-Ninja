from __future__ import annotations

import re

from core.models import Profile


PRODUCTION_WORDS = {"production", "owned", "built", "shipped", "launched", "deployed"}

# High-risk factual tokens that must be traceable to the uploaded resume:
# percentages, money, counted nouns (users/customers/etc), and team sizes.
# The job description is a targeting source, never candidate evidence.
HIGH_RISK_METRIC_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*%"
    r"|\$\s*\d[\d,.]*\s*(?:[kKmMbB]\b|million|billion|thousand)?"
    r"|\b\d[\d,]*\+?\s+(?:users?|customers?|clients?|engineers?|people|employees|platforms?|stores?|sites?|countries|launches)\b"
    r"|\bteam\s+of\s+\d+\b"
    r"|\b(?:millions?|billions?|thousands?|hundreds?)\s+of\s+\w+",
    flags=re.IGNORECASE,
)


def validate_claims(text: str, profile: Profile) -> list[str]:
    """Validate generated output against the candidate's own resume evidence.

    Every check compares the generated text with what the uploaded resume
    (``profile.raw_markdown``) actually says. Content the candidate wrote
    themselves is supported by definition; only claims with no trace in the
    source are flagged.
    """
    errors: list[str] = []
    comparable = _latex_unescape(text)
    lowered = comparable.lower()
    evidence = _normalize(profile.raw_markdown)
    bullet_evidence = _normalize(
        " ".join(bullet for experience in profile.experiences for bullet in experience.bullets)
    )

    for email in profile.retired_emails:
        if email.lower() in lowered:
            errors.append(f"retired email used: {email}")

    errors.extend(_validate_emails(comparable, profile, evidence))
    errors.extend(_validate_high_risk_metrics(comparable, evidence))

    experience_text = _section_between(comparable, "Professional Experience", "Education")
    experience_lowered = _normalize(experience_text)
    for term, display in profile.tier_c.items():
        if len(term) < 3:
            continue
        if _term_in(term, experience_lowered) and not _term_in(term, bullet_evidence):
            errors.append(f"Tier C term in experience bullets: {display}")

    for term in list(profile.tier_b) + list(profile.tier_c):
        if len(term) < 3 or _term_in(term, bullet_evidence):
            continue
        if _term_in(term, experience_lowered) and _near_production_claim(experience_lowered, term):
            errors.append(f"unsupported production ownership claim for {term}")

    if "\\resumeSubheading" in text or "Professional Experience" in text:
        errors.extend(_validate_official_titles(comparable, profile))
        errors.extend(_validate_known_companies(text, profile))
    return _dedupe(errors)


def _validate_high_risk_metrics(text: str, evidence: str) -> list[str]:
    """Flag any percentage, dollar amount, count, or team size absent from the resume."""
    errors: list[str] = []
    for match in HIGH_RISK_METRIC_PATTERN.finditer(text):
        metric = _normalize(match.group(0))
        if metric and metric not in evidence:
            errors.append(f"unsupported metric: {match.group(0).strip()}")
    return errors


def _validate_emails(text: str, profile: Profile, evidence: str) -> list[str]:
    allowed = {profile.contact.email.lower()} if profile.contact.email else set()
    errors: list[str] = []
    for email in re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        normalized = email.lower()
        if normalized in allowed or normalized in evidence:
            continue
        errors.append(f"email not present in resume: {email}")
    return errors


def _near_production_claim(text: str, term: str) -> bool:
    pattern = rf"(?:{'|'.join(PRODUCTION_WORDS)}).{{0,60}}{re.escape(term)}|{re.escape(term)}.{{0,60}}(?:{'|'.join(PRODUCTION_WORDS)})"
    return bool(re.search(pattern, text))


def _validate_official_titles(text: str, profile: Profile) -> list[str]:
    errors: list[str] = []
    for experience in profile.experiences:
        if experience.company and experience.title and experience.company in text:
            company_index = text.find(experience.company)
            block = text[company_index : company_index + 320]
            if experience.title not in block:
                errors.append(f"official title altered for {experience.company}")
    return errors


def _validate_known_companies(text: str, profile: Profile) -> list[str]:
    errors: list[str] = []
    allowed = [_normalize(company) for company in profile.allowed_companies if company]
    experience_text = _section_between(text, "Professional Experience", "Education") or text
    for match in re.finditer(r"\\resumeSubheading\s*\{([^}]+)\}", experience_text):
        company = re.sub(r"\\href\{[^}]+\}\{([^}]+)\}", r"\1", match.group(1)).strip()
        company = _normalize(_latex_unescape(company))
        if not company:
            continue
        if not any(company in known or known in company for known in allowed):
            errors.append(f"invented or unsupported employer: {company}")
    return errors


def _term_in(term: str, text: str) -> bool:
    return bool(re.search(rf"(?<![\w+#.-]){re.escape(term.lower())}(?![\w+#.-])", text))


def _section_between(text: str, start: str, end: str) -> str:
    pattern = rf"{re.escape(start)}(.*?){re.escape(end)}"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def _normalize(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return collapsed.replace(" %", "%").replace("$ ", "$")


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
