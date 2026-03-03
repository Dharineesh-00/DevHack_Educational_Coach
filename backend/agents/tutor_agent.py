"""
TutorAgent — a Socratic DSA interviewer.

Takes the user's code, the Piston execution output, and the complexity
analysis as context, then guides the user with probing questions rather
than handing them the solution.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent

_SYSTEM_PROMPT = """\
You are an expert Socratic DSA (Data Structures & Algorithms) tutor conducting a live coding interview.

Your role:
- Ask probing, thought-provoking questions that guide the candidate toward discovering improvements themselves.
- NEVER reveal, write, or suggest the final correct code or a complete solution.
- NEVER give away the answer directly — always respond with a question or a subtle hint.
- Point out what the candidate got right before raising a concern.
- When referencing complexity, ask "Why did you choose this approach?" rather than stating a better one.
- Keep your response concise (2–4 sentences + 1–2 guiding questions).
- Be encouraging but rigorous.

You will receive:
1. The candidate's Python code.
2. The execution output (stdout/stderr) from running that code.
3. A complexity analysis (time complexity, space complexity, is_optimal flag).

Use all three pieces of context to frame your Socratic questions.
"""


class TutorAgent(BaseAgent):
    """Socratic DSA interviewer — guides without giving away the answer."""

    def __init__(self, model: str = "phi3:latest") -> None:
        super().__init__(
            system_prompt=_SYSTEM_PROMPT,
            model=model,
            json_mode=False,  # free-form conversational text
        )

    async def analyze(  # type: ignore[override]
        self,
        context: str,
        user_prompt: str,
    ) -> str:
        return await super().analyze(context=context, user_prompt=user_prompt)

    @staticmethod
    def build_context(
        code: str,
        execution_output: str,
        complexity: dict,
    ) -> str:
        """
        Build the structured context string sent to the model.

        Args:
            code:             The candidate's submitted Python code.
            execution_output: stdout/stderr from Piston.
            complexity:       Parsed dict from ComplexityAgent.
        """
        return (
            f"### Candidate's Code\n```python\n{code}\n```\n\n"
            f"### Execution Output\n```\n{execution_output or '(no output)'}\n```\n\n"
            f"### Complexity Analysis\n"
            f"- Time complexity : {complexity.get('time_complexity', 'unknown')}\n"
            f"- Space complexity: {complexity.get('space_complexity', 'unknown')}\n"
            f"- Is optimal      : {complexity.get('is_optimal', False)}"
        )
