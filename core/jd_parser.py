from __future__ import annotations

import re
from collections import Counter

from core.models import JDProfile, Profile
from core.profile_loader import cached_profile


COMMON_TECH_TERMS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "sql",
    "postgresql",
    "dbt",
    "etl",
    "elt",
    "tableau",
    "power bi",
    "azure",
    "aws",
    "gcp",
    "docker",
    "kubernetes",
    "spring",
    "hibernate",
    "rest",
    "microservices",
    "react",
    "react native",
    "node.js",
    "mongodb",
    "fastapi",
    "graphql",
    "c#",
    ".net",
    "machine learning",
    "ml",
    "llm",
    "rag",
    "openai",
    "gemini",
    "salesforce",
    "hubspot",
    "snowflake",
    "looker",
    "spark",
    "airflow",
    "scikit-learn",
]


def parse_jd(job_description: str, profile: Profile | None = None) -> JDProfile:
    """Parse a job description into structured planning fields."""
    profile = profile or cached_profile()
    text = job_description or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = _extract_title(text, lines)
    company = _extract_company(text, lines)
    required = _extract_section_items(lines, ["required", "requirements", "qualifications", "must have"])
    preferred = _extract_section_items(lines, ["preferred", "nice to have", "bonus"])
    responsibilities = _extract_section_items(lines, ["responsibilities", "what you will do", "duties", "role"])
    keywords = _extract_keywords(text, profile)
    work_mode = _extract_work_mode(text)
    location = _extract_location(text, lines)
    domain = _extract_domain(text)
    ats = _extract_ats_platform(text)

    if not required:
        required = _sentences_with_keywords(text, keywords[:6])
    if not responsibilities:
        responsibilities = _sentences_with_keywords(text, keywords[:5])[:5]

    return JDProfile(
        title=title or "Target Role",
        company=company or "Target Company",
        work_mode=work_mode,
        location=location,
        required_qualifications=required[:8],
        preferred_qualifications=preferred[:8],
        responsibilities=responsibilities[:5],
        technical_keywords=keywords[:18],
        domain=domain,
        ats_platform=ats,
    )


def _extract_title(text: str, lines: list[str]) -> str:
    patterns = [
        r"(?:job title|position|role)\s*[:\-]\s*([^\n|]+)",
        r"hiring\s+(?:a|an)\s+([A-Z][A-Za-z0-9 /&+#.-]{3,70})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_title(match.group(1))

    for line in lines[:8]:
        lowered = line.lower()
        if any(word in lowered for word in ["engineer", "developer", "analyst", "scientist", "architect"]):
            if len(line) <= 90 and not line.endswith("."):
                return _clean_title(line)
    return ""


def _extract_company(text: str, lines: list[str]) -> str:
    patterns = [
        r"(?:company|organization|employer)\s*[:\-]\s*([^\n|]+)",
        r"\bat\s+([A-Z][A-Za-z0-9 &.,-]{2,60})\s+(?:is|we are|seeks|seeking|hiring)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _trim_company(match.group(1))

    for line in lines[:6]:
        if line.lower().startswith("about "):
            return _trim_company(line[6:])
    return ""


def _extract_section_items(lines: list[str], headings: list[str]) -> list[str]:
    items: list[str] = []
    active = False
    for line in lines:
        lowered = line.lower().strip(":")
        if any(heading in lowered for heading in headings) and len(line) < 80:
            active = True
            continue
        if active and re.match(r"^[A-Z][A-Za-z /&-]{2,40}:?$", line) and len(line) < 60:
            break
        if active:
            cleaned = re.sub(r"^[\-*•]\s*", "", line).strip()
            if cleaned:
                items.append(cleaned)
    return items


def _extract_keywords(text: str, profile: Profile) -> list[str]:
    lowered = text.lower()
    candidates = set(COMMON_TECH_TERMS)
    candidates.update(profile.tier_a.keys())
    candidates.update(profile.tier_b.keys())
    candidates.update(profile.tier_c.keys())
    candidates.update(profile.adjacency.keys())

    found: list[str] = []
    for term in sorted(candidates, key=len, reverse=True):
        if re.search(rf"(?<![\w+#.-]){re.escape(term.lower())}(?![\w+#.-])", lowered):
            display = _display_keyword(term, profile)
            if display not in found:
                found.append(display)

    tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{2,}\b", lowered)
    counts = Counter(tokens)
    for token, count in counts.most_common(20):
        if count > 1 and token not in {"the", "and", "for", "with", "you", "our"}:
            display = _display_keyword(token, profile)
            if display not in found:
                found.append(display)
    return found


def _display_keyword(term: str, profile: Profile) -> str:
    normalized = term.lower()
    for source in [profile.tier_a, profile.tier_b, profile.tier_c]:
        if normalized in source:
            return source[normalized]
    return {
        "aws": "AWS",
        "gcp": "GCP",
        "rag": "RAG",
        "llm": "LLM",
        "ml": "ML",
        "rest": "REST APIs",
    }.get(normalized, term)


def _extract_work_mode(text: str) -> str:
    lowered = text.lower()
    if "hybrid" in lowered:
        return "hybrid"
    if "remote" in lowered:
        return "remote"
    if "on-site" in lowered or "onsite" in lowered or "in office" in lowered:
        return "on-site"
    if "relocat" in lowered:
        return "relocation"
    return "unknown"


def _extract_location(text: str, lines: list[str]) -> str:
    match = re.search(r"(?:location|based in)\s*[:\-]\s*([^\n|]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    for line in lines[:12]:
        if any(place in line.lower() for place in ["toronto", "ontario", "canada", "remote", "hybrid"]):
            return line[:90].strip()
    return ""


def _extract_domain(text: str) -> str:
    lowered = text.lower()
    domains = [
        ("medical device", "medical device"),
        ("healthcare", "healthcare"),
        ("finance", "finance"),
        ("mining", "mining"),
        ("commerce", "commerce"),
        ("saas", "SaaS"),
        ("ai", "AI"),
        ("data", "data"),
    ]
    for needle, domain in domains:
        if needle in lowered:
            return domain
    return ""


def _extract_ats_platform(text: str) -> str:
    lowered = text.lower()
    for platform in ["workday", "greenhouse", "lever", "ashby", "icims", "bamboohr"]:
        if platform in lowered:
            return platform
    return "unknown"


def _sentences_with_keywords(text: str, keywords: list[str]) -> list[str]:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
    matched: list[str] = []
    for sentence in sentences:
        if any(keyword.lower() in sentence.lower() for keyword in keywords):
            matched.append(sentence)
    return matched


def _clean_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -|")
    return cleaned[:80]


def _trim_company(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -|.")
    return cleaned[:70]
