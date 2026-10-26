"""On-device LLM client: talks to a *local* model server (Ollama, or any OpenAI-compatible local server).

Privacy: by default only loopback addresses are accepted, so draft text never leaves the machine.
Reliability: every failure becomes a typed error the caller turns into the rule-based fallback.
Security: prompts, responses and API keys are never logged (only backend, model, status and duration).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests

LOGGER = logging.getLogger("signal_studio.llm")
LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}
DEFAULT_ENDPOINTS = (("ollama", "http://127.0.0.1:11434"), ("openai_compat", "http://127.0.0.1:1234/v1"))
_BUSY = threading.Lock()


class LLMError(Exception):
    """Base class; ``user_message`` is safe to show in the UI (never contains prompts or keys)."""

    user_message = "The local language model failed."

    def __init__(self, detail: str = ""):
        super().__init__(detail or self.user_message)


class LLMUnavailable(LLMError):
    user_message = "No local language model is running."


class LLMModelMissing(LLMUnavailable):
    user_message = "A configured local model is not installed."


class LLMTimeout(LLMError):
    user_message = "The local language model took too long."


class LLMBusy(LLMError):
    user_message = "The local language model is already generating another answer."


class LLMBadResponse(LLMError):
    user_message = "The local language model returned an unusable response."


@dataclass(frozen=True)
class LLMConfig:
    backend: str = "auto"                     # auto | ollama | openai_compat | none
    base_url: str | None = None
    model: str | None = None                  # explicit override of the automatic choice
    fallback_model: str | None = "qwen2.5:0.5b"   # lite model tried when the main one fails ("" or "none" disables)
    total_budget_s: float = 420.0             # stop trying further models after this long
    timeout_s: float = 240.0
    num_ctx: int = 4096
    max_tokens: int = 900
    api_key: str | None = field(default=None, repr=False)   # optional, for local servers that require one
    allow_remote: bool = False

    @property
    def enabled(self) -> bool:
        return self.backend != "none"


def config_from_env(env: dict[str, str] | None = None) -> LLMConfig:
    env = dict(os.environ if env is None else env)
    config = LLMConfig(
        backend=env.get("LLM_BACKEND", "auto").strip().lower() or "auto",
        base_url=(env.get("LLM_BASE_URL") or "").strip() or None,
        model=(env.get("LLM_MODEL") or "").strip() or None,
        fallback_model=(lambda v: None if v.lower() in {"", "none"} else v)(env.get("LLM_FALLBACK_MODEL", "qwen2.5:0.5b").strip()),
        total_budget_s=float(env.get("LLM_TOTAL_BUDGET_S", "420")),
        timeout_s=float(env.get("LLM_TIMEOUT_S", "240")),
        num_ctx=int(env.get("LLM_NUM_CTX", "4096")),
        max_tokens=int(env.get("LLM_MAX_TOKENS", "900")),
        api_key=(env.get("LLM_API_KEY") or "").strip() or None,
        allow_remote=env.get("LLM_ALLOW_REMOTE", "0") == "1",
    )
    if config.backend not in {"auto", "ollama", "openai_compat", "none"}:
        raise ValueError(f"LLM_BACKEND must be auto, ollama, openai_compat or none (got {config.backend!r})")
    if config.base_url and not config.allow_remote and (urlparse(config.base_url).hostname or "") not in LOOPBACK:
        raise ValueError("LLM_BASE_URL must be a loopback address (127.0.0.1/localhost) unless LLM_ALLOW_REMOTE=1")
    return config


def _headers(config: LLMConfig) -> dict[str, str]:
    return {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}


def _candidates(config: LLMConfig) -> list[tuple[str, str]]:
    if config.base_url:
        backend = "ollama" if config.backend in {"auto", "ollama"} and ":11434" in config.base_url else (
            "openai_compat" if config.backend == "auto" else config.backend)
        return [(backend, config.base_url.rstrip("/"))]
    if config.backend in {"ollama", "openai_compat"}:
        return [e for e in DEFAULT_ENDPOINTS if e[0] == config.backend]
    return list(DEFAULT_ENDPOINTS)


def list_models(config: LLMConfig, probe_timeout_s: float = 2.0) -> tuple[str, str, list[str]]:
    """Find a running local server: returns (backend, base_url, installed model names)."""
    for backend, url in _candidates(config):
        try:
            if backend == "ollama":
                response = requests.get(f"{url}/api/tags", timeout=probe_timeout_s, headers=_headers(config))
                response.raise_for_status()
                names = [m["name"] for m in response.json().get("models", [])]
            else:
                response = requests.get(f"{url}/models", timeout=probe_timeout_s, headers=_headers(config))
                response.raise_for_status()
                names = [m["id"] for m in response.json().get("data", [])]
            return backend, url, names
        except (requests.RequestException, ValueError, KeyError, TypeError):
            continue
    raise LLMUnavailable("no local model server answered on the default ports")


def generate_json(config: LLMConfig, backend: str, base_url: str, model: str, system: str, user: str,
                  schema: dict | None = None) -> str:
    """One chat completion that should return JSON text. Raises LLMError subclasses only."""
    if not _BUSY.acquire(blocking=False):
        raise LLMBusy()
    started = time.perf_counter()
    status = "error"
    try:
        for attempt in (1, 2):
            try:
                if backend == "ollama":
                    response = requests.post(
                        f"{base_url}/api/chat", headers=_headers(config), timeout=config.timeout_s,
                        json={"model": model, "stream": False, "format": schema or "json",
                              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                              "options": {"temperature": 0.2, "num_ctx": config.num_ctx, "num_predict": config.max_tokens}})
                else:
                    response = requests.post(
                        f"{base_url}/chat/completions", headers=_headers(config), timeout=config.timeout_s,
                        json={"model": model, "temperature": 0.2, "max_tokens": config.max_tokens,
                              "response_format": {"type": "json_object"},
                              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            except requests.Timeout as error:
                status = "timeout"
                raise LLMTimeout() from error
            except requests.ConnectionError as error:
                if attempt == 1:
                    time.sleep(0.5)
                    continue
                status = "unreachable"
                raise LLMUnavailable() from error
            if response.status_code == 404:
                status = "model-missing"
                raise LLMModelMissing(f"model '{model}' is not installed on the local server")
            if response.status_code >= 500 and attempt == 1:
                time.sleep(0.5)
                continue
            if response.status_code != 200:
                status = f"http-{response.status_code}"
                raise LLMBadResponse(f"local server answered HTTP {response.status_code}")
            try:
                payload = response.json()
                content = payload["message"]["content"] if backend == "ollama" else payload["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as error:
                status = "bad-envelope"
                raise LLMBadResponse() from error
            if not isinstance(content, str) or not content.strip():
                status = "empty"
                raise LLMBadResponse("the model returned no text")
            status = "ok"
            return content
        raise LLMUnavailable()  # pragma: no cover - loop always returns or raises
    finally:
        LOGGER.info("llm call backend=%s model=%s status=%s seconds=%.1f", backend, model, status, time.perf_counter() - started)
        _BUSY.release()
