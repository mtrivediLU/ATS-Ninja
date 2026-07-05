from __future__ import annotations

from typing import Any

from core.models import Profile
from core.resume_extractor import extract_profile


def build_profile(resume_text: str, llm: Any | None = None) -> Profile:
    """Build the candidate's Profile strictly from their uploaded resume text.

    This is the single source of truth for the pipeline: every fact used
    downstream (skills tiers, experience bullets, education, certifications)
    is derived from what the candidate actually submitted, not from any
    hardcoded personal data.
    """
    return extract_profile(resume_text, llm=llm)


def empty_profile() -> Profile:
    """Return a blank Profile for call sites that need a placeholder before
    a resume has been uploaded (e.g. early keyword extraction defaults)."""
    return extract_profile("")


# Backwards-compatible alias for existing call sites/tests that expect a
# no-argument profile getter. Returns an empty, non-hardcoded profile.
def cached_profile() -> Profile:
    return empty_profile()
