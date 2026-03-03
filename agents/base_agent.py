"""
Base agent that every specialised agent should inherit from.

Usage::

    class CodeReviewAgent(BaseAgent):
        def __init__(self):
            super().__init__(
                system_prompt="You are an expert code reviewer.",
                model="phi3:latest",
            )

    agent = CodeReviewAgent()
    result = await agent.analyze(
        context="def add(a, b): return a - b",
        user_prompt="Find the bug in this function.",
    )
"""

from __future__ import annotations

from services.llm_client import OllamaClient


class BaseAgent:
    """
    Abstract async agent backed by a local Ollama model.

    Parameters
    ----------
    system_prompt:
        Instruction text that shapes the model's persona / behaviour for
        every call made through this agent.
    model:
        Ollama model tag to use (default: ``"phi3:latest"``).
    json_mode:
        When ``True``, passes ``format="json"`` to Ollama so the model is
        instructed to respond with valid JSON only.
    timeout:
        HTTP timeout in seconds forwarded to :class:`OllamaClient`.
    """

    def __init__(
        self,
        system_prompt: str,
        model: str = "phi3:latest",
        *,
        json_mode: bool = False,
        timeout: float = 120.0,
    ) -> None:
        self.system_prompt = system_prompt
        self.json_mode = json_mode
        self._client = OllamaClient(model=model, timeout=timeout)

    # ------------------------------------------------------------------
    # Core method – override in subclasses to customise behaviour
    # ------------------------------------------------------------------

    async def analyze(self, context: str, user_prompt: str) -> str:
        """
        Run the agent against a given context and user instruction.

        The final prompt sent to the model is::

            [context]
            ---
            [user_prompt]

        The *system prompt* set at construction time is passed separately
        so the model keeps its persona across calls.

        Args:
            context:     Background information, code, data, etc.
            user_prompt: The question or task for the agent to perform.

        Returns:
            The model's complete response as a plain string (or a JSON
            string when ``json_mode=True``).
        """
        combined_prompt = self._build_prompt(context, user_prompt)

        response = await self._client.generate(
            prompt=combined_prompt,
            system=self.system_prompt,
            format="json" if self.json_mode else None,
        )
        return response

    # ------------------------------------------------------------------
    # Streaming variant – yields text chunks for SSE / WebSocket use
    # ------------------------------------------------------------------

    async def analyze_stream(self, context: str, user_prompt: str):
        """
        Streaming version of :meth:`analyze`.

        Yields text chunks as they arrive from Ollama::

            async for chunk in agent.analyze_stream(ctx, prompt):
                print(chunk, end="", flush=True)
        """
        combined_prompt = self._build_prompt(context, user_prompt)

        async for chunk in self._client.stream_generate(
            prompt=combined_prompt,
            system=self.system_prompt,
            format="json" if self.json_mode else None,
        ):
            yield chunk

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(context: str, user_prompt: str) -> str:
        """Combine context and user prompt into a single string."""
        if context.strip():
            return f"{context.strip()}\n---\n{user_prompt.strip()}"
        return user_prompt.strip()
