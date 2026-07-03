from __future__ import annotations

import os
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


DEFAULT_MODEL = "llama3.2"
DEFAULT_BASE_URL = "http://localhost:11434"

if load_dotenv is not None:
    load_dotenv()


def get_llm(model_name: str = DEFAULT_MODEL, temperature: float = 0.3) -> ChatOllama:
    """Return a configured local Ollama chat model."""
    model = (model_name or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL).strip()
    base_url = (os.getenv("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=temperature,
    )


def test_ollama_connection(timeout: float = 3.0) -> bool:
    """Return True when the local Ollama API responds to the tags endpoint."""
    base_url = (os.getenv("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    request = Request(f"{base_url}/api/tags", method="GET")

    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, URLError, TimeoutError):
        return False
