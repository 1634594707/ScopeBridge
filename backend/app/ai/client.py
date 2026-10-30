"""Minimal OpenAI-compatible chat client.

One request per call, no retries: a model failure is reported to the studio so a
human can price the scope by hand. Retrying silently would hide the failure and
produce duplicate evidence rows.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.core.errors import ApiError

logger = logging.getLogger("scopebridge.model")


def complete_json(
    *,
    model: str,
    base_url: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float,
) -> tuple[str, int]:
    """Return (raw content, latency in milliseconds)."""
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    started = time.perf_counter()
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning("model call failed after transport error: %s", exc.__class__.__name__)
        raise ApiError(
            502,
            "model_unavailable",
            "The model endpoint could not be reached. Price the scope by hand or retry.",
            {"reason": exc.__class__.__name__},
        ) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)

    if response.status_code >= 400:
        raise ApiError(
            502,
            "model_http_error",
            f"The model endpoint returned HTTP {response.status_code}.",
        )

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ApiError(
            502,
            "model_bad_response",
            "The model endpoint returned a shape this build does not understand.",
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise ApiError(
            502,
            "model_empty_response",
            "The model returned an empty answer. Price the scope by hand or retry.",
        )

    return content, latency_ms
