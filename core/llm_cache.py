from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

try:
    import diskcache
except ImportError:  # pragma: no cover - optional until dependencies are installed
    diskcache = None  # type: ignore


CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "llm"
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # one week

_cache: Any | None = None
if diskcache is not None:
    try:
        _cache = diskcache.Cache(str(CACHE_DIR))
    except Exception:  # pragma: no cover - filesystem issues fall back to no cache
        _cache = None


def cache_enabled() -> bool:
    """Allow disabling the cache with ATS_NINJA_LLM_CACHE=0, e.g. to force fresh output."""
    return _cache is not None and os.getenv("ATS_NINJA_LLM_CACHE", "1") != "0"


def make_key(identity: str, prompt: str) -> str:
    return hashlib.sha256(f"{identity}\n{prompt}".encode("utf-8")).hexdigest()


def get(key: str) -> Any | None:
    if not cache_enabled():
        return None
    try:
        return _cache.get(key)
    except Exception:  # pragma: no cover - never let cache errors break generation
        return None


def set(key: str, value: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    if not cache_enabled():
        return
    try:
        _cache.set(key, value, expire=ttl_seconds)
    except Exception:  # pragma: no cover - never let cache errors break generation
        pass
