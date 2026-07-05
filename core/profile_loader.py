from __future__ import annotations

from typing import Any

from core import llm_cache
from core.models import Profile
from core.resume_extractor import extract_profile


def build_profile(resume_text: str, llm: Any | None = None) -> Profile:
    """Build the candidate's Profile strictly from their uploaded resume text.

    This is the single source of truth for the pipeline: every fact used
    downstream (skills tiers, experience bullets, education, certifications)
    is derived from what the candidate actually submitted, not from any
    hardcoded personal data.

    The parsed profile is cached on disk keyed by the resume content hash,
    so the same resume never pays for LLM extraction twice, including
    across app restarts and Streamlit reruns.
    """
    text = (resume_text or "").strip()
    if not text:
        return extract_profile("")

    extractor = getattr(llm, "model", "heuristic") if llm is not None else "heuristic"
    key = llm_cache.make_key(f"profile|{extractor}", text)
    cached = llm_cache.get(key)
    if isinstance(cached, Profile):
        return cached

    profile = extract_profile(text, llm=llm)
    if profile.experiences or profile.tier_a:
        llm_cache.set(key, profile)
    return profile


def empty_profile() -> Profile:
    """Return a blank Profile for call sites that need a placeholder before
    a resume has been uploaded (e.g. early keyword extraction defaults)."""
    return extract_profile("")


# Backwards-compatible alias for existing call sites/tests that expect a
# no-argument profile getter. Returns an empty, non-hardcoded profile.
def cached_profile() -> Profile:
    return empty_profile()
