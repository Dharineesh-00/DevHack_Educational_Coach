"""
Async client for OpenRouter (https://openrouter.ai).

Primary model : anthropic/claude-3-haiku
Fallback models: free-tier models tried in order when the primary fails.

Supports:
  - generate()      : returns the full response text.
  - stream_generate(): async-generator that yields text chunks.
  - chat()          : OpenAI-style multi-turn messages interface.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter settings
# ---------------------------------------------------------------------------
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = "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"
PRIMARY_MODEL       = "anthropic/claude-3-haiku"

# Free-tier fallback models tried in order when the primary fails.
FALLBACK_MODELS: list[str] = [
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2-7b-instruct:free",
]

DEFAULT_TIMEOUT = 60.0


class OpenRouterClient:
    """
    Async HTTP client wrapping the OpenRouter /chat/completions endpoint.

    Usage::

        client = OpenRouterClient()

        # full response
        text = await client.generate("Explain Big-O notation.")

        # streaming
        async for chunk in client.stream_generate("Tell me a story"):
            print(chunk, end="", flush=True)

        # multi-turn chat
        reply = await client.chat([
            {"role": "system", "content": "You are a helpful tutor."},
            {"role": "user",   "content": "What is a stack?"},
        ])
    """

    def __init__(
        self,
        api_key: str = OPENROUTER_API_KEY,
        model: str = PRIMARY_MODEL,
        fallback_models: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key         = api_key
        self.model           = model
        self.fallback_models = fallback_models if fallback_models is not None else FALLBACK_MODELS
        self.timeout         = timeout
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:8000",
            "X-Title":       "DSA Tutor",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        model: str | None = None,
        format: str | None = None,   # kept for API compatibility, ignored
        options: dict | None = None,
    ) -> str:
        """
        Send a prompt and return the full response text.
        Tries the primary model first, then each fallback in order.
        """
        models_to_try = [model or self.model] + self.fallback_models
        last_exc: Exception | None = None

        for attempt_model in models_to_try:
            try:
                result = await self._complete(
                    prompt=prompt,
                    system=system,
                    model=attempt_model,
                    options=options or {},
                )
                if attempt_model != (model or self.model):
                    logger.warning(
                        "[OpenRouter] Primary failed; used fallback: %s", attempt_model
                    )
                return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("[OpenRouter] Model %s failed: %s", attempt_model, exc)
                last_exc = exc

        raise RuntimeError(
            f"All OpenRouter models failed. Last error: {last_exc}"
        ) from last_exc

    async def stream_generate(
        self,
        prompt: str,
        *,
        system: str = "",
        model: str | None = None,
        format: str | None = None,   # kept for API compatibility, ignored
        options: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the response, yielding text chunks as they arrive.
        Falls back through free models on failure.
        """
        models_to_try = [model or self.model] + self.fallback_models
        last_exc: Exception | None = None

        for attempt_model in models_to_try:
            try:
                async for chunk in self._stream_complete(
                    prompt=prompt,
                    system=system,
                    model=attempt_model,
                    options=options or {},
                ):
                    yield chunk
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[OpenRouter] Streaming model %s failed: %s", attempt_model, exc
                )
                last_exc = exc

        raise RuntimeError(
            f"All OpenRouter models failed during streaming. Last error: {last_exc}"
        ) from last_exc

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        options: dict | None = None,
    ) -> str:
        """
        Send an OpenAI-style messages list and return the assistant reply.
        Automatically falls back to free models on failure.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            model:    Override model for this call.
            options:  Extra payload fields (e.g. {"max_tokens": 512}).
        """
        models_to_try = [model or self.model] + self.fallback_models
        last_exc: Exception | None = None

        for attempt_model in models_to_try:
            try:
                payload: dict = {
                    "model": attempt_model,
                    "messages": messages,
                    **(options or {}),
                }
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=self._headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content: str = data["choices"][0]["message"]["content"]
                    if attempt_model != (model or self.model):
                        logger.warning(
                            "[OpenRouter] Primary failed; used fallback: %s", attempt_model
                        )
                    return content
            except Exception as exc:  # noqa: BLE001
                logger.warning("[OpenRouter] Chat model %s failed: %s", attempt_model, exc)
                last_exc = exc

        raise RuntimeError(
            f"All OpenRouter models failed for chat. Last error: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _complete(
        self,
        prompt: str,
        system: str,
        model: str,
        options: dict,
    ) -> str:
        """Non-streaming single completion."""
        messages = self._build_messages(prompt, system)
        payload: dict = {"model": model, "messages": messages, **options}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_complete(
        self,
        prompt: str,
        system: str,
        model: str,
        options: dict,
    ) -> AsyncGenerator[str, None]:
        """SSE streaming completion."""
        messages = self._build_messages(prompt, system)
        payload: dict = {"model": model, "messages": messages, "stream": True, **options}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    raw_line = raw_line.strip()
                    if not raw_line or raw_line == "data: [DONE]":
                        continue
                    if raw_line.startswith("data: "):
                        data = json.loads(raw_line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        token: str = delta.get("content", "")
                        if token:
                            yield token

    @staticmethod
    def _build_messages(prompt: str, system: str) -> list[dict]:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — existing imports still work unchanged
# ---------------------------------------------------------------------------
OllamaClient = OpenRouterClient
