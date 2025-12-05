"""Utilities for working with Ollama endpoints."""

from typing import Optional
from urllib.parse import urlparse

DEFAULT_OLLAMA_HOST = "http://localhost:11434"

def normalize_ollama_host(raw_host: Optional[str], default_host: str = DEFAULT_OLLAMA_HOST) -> str:
    """Normalize host strings so HTTP clients always get a valid base URL."""
    if not raw_host:
        return default_host

    host = raw_host.strip().rstrip("/")
    if not host:
        return default_host

    if "://" not in host:
        host = f"http://{host}"

    parsed = urlparse(host)
    netloc = parsed.netloc or parsed.path
    if not netloc:
        return default_host

    if ":" not in netloc and not netloc.endswith("]"):
        netloc = f"{netloc}:11434"

    normalized = parsed._replace(netloc=netloc, path="", params="", query="", fragment="")
    return normalized.geturl().rstrip("/")
