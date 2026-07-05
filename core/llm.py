from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until dependencies are installed
    load_dotenv = None

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover - compatibility fallback
    from langchain_community.chat_models import ChatOllama  # type: ignore

from core import llm_cache


logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.2"
DEFAULT_BASE_URL = "http://localhost:11434"

# Output-length caps per task shape. Ollama keeps generating until it hits a
# stop token or this cap; bounding it is the single biggest lever on latency
# for small, well-scoped generations (a one-line bullet does not need a
# 2000-token budget), while extraction tasks get more room because a full
# resume/JD can legitimately produce a large JSON payload.
NUM_PREDICT_SHORT = 700
NUM_PREDICT_EXTRACTION = 2048

T = TypeVar("T")

if load_dotenv is not None:
    load_dotenv()


def get_llm(
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    num_predict: int | None = None,
) -> ChatOllama:
    """Return a configured local Ollama chat model."""
    model = (model_name or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL).strip()
    base_url = (os.getenv("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    kwargs: dict[str, Any] = {"model": model, "base_url": base_url, "temperature": temperature}
    if num_predict is not None:
        kwargs["num_predict"] = num_predict
    return ChatOllama(**kwargs)


def test_ollama_connection(timeout: float = 3.0) -> bool:
    """Return True when the local Ollama API responds to the tags endpoint."""
    base_url = (os.getenv("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    request = Request(f"{base_url}/api/tags", method="GET")

    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, URLError, TimeoutError):
        return False


def get_llm_if_available(
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    num_predict: int | None = None,
) -> Any | None:
    """Return a chat model only when Ollama is actually reachable, else None.

    Every generation step in this app is written to work without an LLM
    (deterministic fallback), so callers should treat None as a normal,
    expected state rather than an error.
    """
    if not test_ollama_connection():
        return None
    try:
        return get_llm(model_name=model_name, temperature=temperature, num_predict=num_predict)
    except Exception:
        logger.exception("Failed to construct local LLM client.")
        return None


def get_llm_pair(model_name: str = DEFAULT_MODEL) -> tuple[Any | None, Any | None]:
    """Return (extraction_llm, short_llm) tuned for their respective task shapes.

    A single connectivity check backs both: either Ollama is reachable and
    you get two differently-capped clients for the same model, or it is not
    and both are None so every caller falls back deterministically.
    """
    if not test_ollama_connection():
        return None, None
    try:
        extraction_llm = get_llm(model_name=model_name, temperature=0.2, num_predict=NUM_PREDICT_EXTRACTION)
        short_llm = get_llm(model_name=model_name, temperature=0.4, num_predict=NUM_PREDICT_SHORT)
        return extraction_llm, short_llm
    except Exception:
        logger.exception("Failed to construct local LLM clients.")
        return None, None


def run_concurrently(tasks: dict[str, Callable[[], T]], max_workers: int | None = None) -> dict[str, T]:
    """Run independent zero-arg callables concurrently and return their results by key.

    Ollama calls are I/O-bound HTTP round trips, so threads (not processes)
    are the right primitive here: whichever tasks the local model server can
    interleave will overlap, and worst case this degrades to sequential with
    negligible thread overhead.
    """
    if len(tasks) <= 1:
        return {key: task() for key, task in tasks.items()}

    results: dict[str, T] = {}
    with ThreadPoolExecutor(max_workers=max_workers or len(tasks)) as executor:
        futures = {key: executor.submit(task) for key, task in tasks.items()}
        for key, future in futures.items():
            results[key] = future.result()
    return results


def _llm_identity(llm: Any) -> str:
    return f"{getattr(llm, 'model', '')}|{getattr(llm, 'temperature', '')}|{getattr(llm, 'num_predict', '')}"


def invoke_text(llm: Any, prompt: str) -> str:
    """Invoke the LLM with a plain prompt and return cleaned text, or '' on failure.

    Identical (model, prompt) pairs are cached on disk so repeated
    generations against unchanged inputs (a very common workflow: same
    resume, several job descriptions, or re-clicking "generate") skip the
    network round trip entirely.
    """
    if llm is None or not prompt.strip():
        return ""

    key = llm_cache.make_key(_llm_identity(llm), prompt)
    cached = llm_cache.get(key)
    if cached is not None:
        return cached

    try:
        result = llm.invoke(prompt)
    except Exception:
        logger.exception("LLM text invocation failed.")
        return ""

    text = _extract_text(result)
    if text:
        llm_cache.set(key, text)
    return text


def invoke_json(
    llm: Any,
    prompt: str,
    *,
    retries: int = 2,
) -> dict[str, Any] | list[Any] | None:
    """Invoke the LLM expecting a JSON object/array back, with self-repair retries.

    Returns None when the LLM is unavailable or never produces parseable JSON,
    so callers can fall back to deterministic logic. Cached the same way as
    invoke_text, keyed off the exact prompt sent for a given attempt.
    """
    if llm is None or not prompt.strip():
        return None

    current_prompt = prompt
    last_raw = ""
    for attempt in range(retries + 1):
        key = llm_cache.make_key(_llm_identity(llm), current_prompt)
        cached = llm_cache.get(key)
        if cached is not None:
            return cached

        try:
            result = llm.invoke(current_prompt)
        except Exception:
            logger.exception("LLM JSON invocation failed on attempt %s.", attempt)
            return None

        raw = _extract_text(result)
        last_raw = raw
        parsed = _parse_json_loose(raw)
        if parsed is not None:
            llm_cache.set(key, parsed)
            return parsed

        current_prompt = (
            f"{prompt}\n\nYour previous reply was not valid JSON:\n{raw}\n\n"
            "Reply again with ONLY a single valid JSON object or array. "
            "No markdown code fences, no commentary, no trailing commas."
        )

    logger.warning("LLM never returned parseable JSON. Last raw output: %.200s", last_raw)
    return None


def _extract_text(result: Any) -> str:
    if isinstance(result, dict):
        value = result.get("text") or result.get("output_text") or result.get("content") or ""
        return str(value).strip()
    content = getattr(result, "content", None)
    if content is not None:
        return str(content).strip()
    return str(result or "").strip()


def _parse_json_loose(raw: str) -> dict[str, Any] | list[Any] | None:
    if not raw:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None
    return None
