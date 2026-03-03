"""
Async client for a locally running Ollama instance.

Supports two modes:
  - full   : waits for the complete response and returns the text string.
  - stream : yields text chunks as they arrive (async generator).

Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_PATH = "/api/generate"
DEFAULT_MODEL = "phi3:latest"  # Change to match your installed Ollama model
DEFAULT_TIMEOUT = 120.0  # Ollama can be slow on first token


class OllamaClient:
    """Async HTTP client wrapping the Ollama /api/generate endpoint."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        model: str | None = None,
        format: str | None = None,  # pass "json" to request JSON-mode output
        options: dict | None = None,  # e.g. {"num_predict": 120, "temperature": 0.75}
    ) -> str:
        """
        Send a prompt to Ollama and return the full response text.

        Args:
            prompt:  The user/instruction prompt.
            system:  Optional system prompt prepended to the conversation.
            model:   Override the default model for this request only.
            format:  Set to ``"json"`` to instruct Ollama to reply with
                     valid JSON (JSON mode).

        Returns:
            The complete generated text as a single string.

        Raises:
            httpx.TimeoutException:   Request exceeded ``self.timeout``.
            httpx.HTTPStatusError:    Ollama returned a non-2xx status.
            httpx.RequestError:       Network/connection problem.
        """
        chunks: list[str] = []
        async for chunk in self._stream_generate(
            prompt=prompt,
            system=system,
            model=model or self.model,
            format=format,
            options=options,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    async def stream_generate(
        self,
        prompt: str,
        *,
        system: str = "",
        model: str | None = None,
        format: str | None = None,
        options: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the Ollama response, yielding text chunks as they arrive.

        Usage::

            async for chunk in client.stream_generate("Tell me a story"):
                print(chunk, end="", flush=True)
        """
        async for chunk in self._stream_generate(
            prompt=prompt,
            system=system,
            model=model or self.model,
            format=format,
            options=options,
        ):
            yield chunk

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _stream_generate(
        self,
        prompt: str,
        system: str,
        model: str,
        format: str | None,
        options: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Core streaming generator — all public methods delegate here."""
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format  # e.g. "json" for JSON-mode
        if options:
            payload["options"] = options  # e.g. {"num_predict": 120, "temperature": 0.75}

        url = f"{self.base_url}{OLLAMA_GENERATE_PATH}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    if not raw_line.strip():
                        continue
                    data = json.loads(raw_line)
                    token: str = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
