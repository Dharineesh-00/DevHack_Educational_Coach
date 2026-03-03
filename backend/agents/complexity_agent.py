"""
ComplexityAgent — analyses Python code and returns a structured JSON object.

Response schema (enforced via Ollama JSON mode)::

    {
        "time_complexity":  "O(n log n)",
        "space_complexity": "O(n)",
        "is_optimal":       true | false
    }
"""

from __future__ import annotations

import json

from agents.base_agent import BaseAgent

_SYSTEM_PROMPT = """\
You are a computer-science complexity analyser.
Your ONLY job is to analyse Python code and return a JSON object — nothing else.

You MUST respond with EXACTLY this JSON structure and no other text:
{
    "time_complexity": "<Big-O notation, e.g. O(n log n)>",
    "space_complexity": "<Big-O notation, e.g. O(n)>",
    "is_optimal": <true or false>
}

Rules:
- Do NOT include markdown, code fences, explanations, or any prose.
- Use standard Big-O notation (e.g. O(1), O(n), O(n^2), O(log n), O(n log n)).
- Set "is_optimal" to true only if no asymptotically better general-purpose algorithm exists for the problem.
- If the code cannot be analysed, still return the JSON with "unknown" for the complexity fields and false for is_optimal.
"""


class ComplexityAgent(BaseAgent):
    """Analyses Python code complexity and returns a validated JSON result."""

    def __init__(self, model: str = "phi3:latest") -> None:
        super().__init__(
            system_prompt=_SYSTEM_PROMPT,
            model=model,
            json_mode=True,   # instructs Ollama to guarantee JSON output
        )

    async def analyze(self, context: str, user_prompt: str) -> str:  # type: ignore[override]
        """
        Analyse the given code and return the raw JSON string from the model.

        For convenience, callers can also use :meth:`analyze_structured` to
        get a parsed ``dict`` directly.
        """
        return await super().analyze(context=context, user_prompt=user_prompt)

    async def analyze_structured(self, code: str) -> dict:
        """
        Convenience wrapper — parses the JSON string and returns a ``dict``.

        Returns a safe fallback dict if the model returns invalid JSON.
        """
        raw = await self.analyze(
            context=code,
            user_prompt="Analyse the time complexity, space complexity, and optimality of the code above.",
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Graceful fallback — the model occasionally wraps JSON in markdown
            # even with json_mode; try to extract the first {...} block.
            import re
            match = re.search(r"\{.*?\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "is_optimal": False,
                "_raw": raw,
            }
