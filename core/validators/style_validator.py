from __future__ import annotations

import re


BANNED_WORDS = [
    "leveraged",
    "spearheaded",
    "architected",
    "orchestrated",
    "streamlined",
    "empowered",
    "enabled",
    "pioneered",
    "championed",
    "synergized",
    "facilitated",
    "elevated",
    "transformed",
    "revolutionized",
    "crafted",
    "curated",
    "robust",
    "seamless",
    "comprehensive",
    "holistic",
    "innovative",
    "dynamic",
    "strategic",
    "pivotal",
    "transformational",
    "high-impact",
    "end-to-end",
    "enterprise-grade",
    "mission-critical",
    "future-proof",
    "cutting-edge",
    "world-class",
    "best-in-class",
    "cloud-native",
    "proven track record",
    "proven expertise",
    "demonstrated ability",
    "hands-on experience",
    "results-driven",
    "detail-oriented",
    "passionate about",
    "adept at",
    "I am excited to apply",
    "I was thrilled to see",
    "esteemed organization",
    "perfect fit",
    "I believe my skills align",
    "I would welcome the opportunity",
    "make a meaningful impact",
    "unique blend of",
]


def validate_style(text: str) -> list[str]:
    """Catch banned punctuation and filler language."""
    errors: list[str] = []
    if "—" in text:
        errors.append("em dash is not allowed")
    if "–" in text:
        errors.append("en dash is not allowed")
    if "--" in text:
        errors.append("double hyphen is not allowed")

    lowered = text.lower()
    for phrase in BANNED_WORDS:
        pattern = rf"\b{re.escape(phrase.lower())}\b"
        if re.search(pattern, lowered):
            errors.append(f"banned style phrase: {phrase}")
    return errors


def assert_style(text: str) -> None:
    """Raise when style validation fails."""
    errors = validate_style(text)
    if errors:
        raise ValueError("; ".join(errors))
