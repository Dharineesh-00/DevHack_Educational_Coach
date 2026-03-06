"""
Orchestrator — the 'Good Cop / Bad Cop Interview Panel' pipeline.

Pipeline
--------
1. Execute the code via Piston (get stdout/stderr).
2. Agent 1 – The Critic     : Ruthless Staff Engineer tears apart the code.
3. Agent 2 – The Defender   : Empathetic DevRel coach counters the Critic.
4. Agent 3 – The Judge      : Lead Interviewer synthesises a Socratic hint.

Returns an :class:`OrchestrationResult` dataclass.  The API layer
packs ``agent_logs`` + ``tutor_response`` into the response JSON so
the React frontend can render the live debate in its agent terminal.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)
_SEP = "=" * 60

# Simple in-memory failure tracker  { user_id: [timestamp, ...] }
# Counts non-zero exit-code submissions within a rolling 5-minute window.
_failure_log: dict[str, list[float]] = defaultdict(list)
_WINDOW = 300  # seconds (5 minutes)


def _record_failure(user_id: str) -> int:
    """Record a failed run and return how many failures in the last 5 min."""
    now = time.time()
    failures = _failure_log[user_id]
    failures.append(now)
    # prune old entries outside the rolling window
    _failure_log[user_id] = [t for t in failures if now - t <= _WINDOW]
    return len(_failure_log[user_id])


def _vibe(failure_count: int) -> str:
    """Return a short frustration signal string for the VIBE log line."""
    if failure_count == 0:
        return "All good."
    if failure_count == 1:
        return "First failure. Stay calm, keep going."
    if failure_count <= 3:
        return f"Failed {failure_count} times in 5 min. Mild frustration."
    return f"Failed {failure_count} times in 5 min. High frustration."

from services.piston_runner import PistonClient
from services.llm_client import OpenRouterClient
from db.base_repo import MetricsRepository
from db.mock_repo import MockMetricsRepository

# Shared singletons (instantiated once at import time)
_piston = PistonClient()
_ollama = OpenRouterClient()  # primary: claude-3-haiku, auto-falls back to free models

# OpenRouter generation options for short, focused agent responses.
_FAST_OPTS: dict = {"max_tokens": 200, "temperature": 0.75}


@dataclass
class OrchestrationResult:
    """Holds every artefact produced by the debate pipeline."""

    # --- Piston execution ---
    language: str
    version: str
    stdout: str
    stderr: str
    execution_output: str  # combined stdout+stderr (Piston "output" field)
    exit_code: int

    # --- Agent debate ---
    agent_logs: list   # list[str]: one formatted line per panel member
    tutor_feedback: str  # Judge's final Socratic response


async def run(
    code: str,
    language: str = "python",
    user_id: str = "anonymous",
    repo: MetricsRepository | None = None,
) -> OrchestrationResult:
    """
    Execute the full DSA analysis pipeline for a submitted code snippet.

    Args:
        code:     Source code submitted by the user.
        language: Piston language identifier (default: ``"python"``).
        user_id:  Identifier for the learner; used when persisting mastery
                  data via ``repo``.
        repo:     A :class:`~db.base_repo.MetricsRepository` implementation.
                  Defaults to :class:`~db.mock_repo.MockMetricsRepository`
                  (logs to console). Swap for a real DB implementation
                  without touching any business logic.

    Returns:
        A fully populated :class:`OrchestrationResult`.

    Raises:
        httpx.TimeoutException:  Piston or Ollama request timed out.
        httpx.HTTPStatusError:   Downstream service returned a non-2xx status.
        httpx.RequestError:      Network error reaching Piston or Ollama.
    """
    if repo is None:
        repo = MockMetricsRepository()

    # ------------------------------------------------------------------
    # Step 1 — Execute code via Piston
    # ------------------------------------------------------------------
    piston_response = await _piston.execute_code(language=language, code=code)
    run_data = piston_response.get("run", {})

    exec_language = piston_response.get("language", language)
    exec_version = piston_response.get("version", "unknown")
    stdout = run_data.get("stdout", "")
    stderr = run_data.get("stderr", "")
    execution_output = run_data.get("output", "")
    exit_code = run_data.get("code", -1)

    logger.info(
        "\n%s\n[EXECUTION] Piston returned: %s\n"
        "             language=%s  version=%s  exit_code=%d\n"
        "             stdout  : %s\n"
        "             stderr  : %s\n%s",
        _SEP,
        (stderr.strip() or stdout.strip() or "(no output)"),
        exec_language, exec_version, exit_code,
        stdout.strip() or "(none)",
        stderr.strip() or "(none)",
        _SEP,
    )

    # Vibe check — track failures and log emotional signal
    failure_count = _record_failure(user_id) if exit_code != 0 else 0
    logger.info("[AGENT: VIBE]  user_id=%s  |  %s", user_id, _vibe(failure_count))

    # ------------------------------------------------------------------
    # Step 2 — Agent 1: The Critic (Ruthless Staff Engineer)
    # ------------------------------------------------------------------
    logger.info("\n%s\n[AGENT: CRITIC] Reviewing submission...", _SEP)

    critic_prompt = (
        f"You are a ruthless Staff Engineer interviewing a candidate. "
        f"Review this code: {code} and this execution output: {execution_output}. "
        f"In exactly 1 or 2 short sentences, roast the time/space complexity or code quality. "
        f"Be harsh but technically accurate. Do not offer solutions."
    )
    critic_review: str = (await _ollama.generate(
        prompt=critic_prompt,
        options=_FAST_OPTS,
    )).strip()

    logger.info("\n[CRITIC]\n%s\n%s", critic_review, _SEP)

    # ------------------------------------------------------------------
    # Step 3 — Agent 2: The Defender (Empathetic DevRel Coach)
    # ------------------------------------------------------------------
    logger.info("\n%s\n[AGENT: DEFENDER] Countering the Critic...", _SEP)

    defender_prompt = (
        f"You are an empathetic junior developer coach. "
        f"The harsh Staff Engineer just said this about the student's code: \"{critic_review}\". "
        f"Look at the user's code: {code}. "
        f"In exactly 1 or 2 short sentences, defend the student. "
        f"Point out one good thing they did (like variable naming, logic, or edge cases). "
        f"Disagree with the Staff Engineer's tone."
    )
    defender_review: str = (await _ollama.generate(
        prompt=defender_prompt,
        options=_FAST_OPTS,
    )).strip()

    logger.info("\n[DEFENDER]\n%s\n%s", defender_review, _SEP)

    # ------------------------------------------------------------------
    # Step 4 — Agent 3: The Judge (Socratic Lead Interviewer)
    # ------------------------------------------------------------------
    logger.info("\n%s\n[AGENT: JUDGE] Synthesising debate...", _SEP)

    judge_prompt = (
        f"You are the Lead Interviewer. "
        f"The Critic said: \"{critic_review}\". "
        f"The Defender said: \"{defender_review}\". "
        f"Synthesize this debate. Write a friendly, 2-sentence response to the student. "
        f"Acknowledge the good (from the Defender), but gently push them to fix the flaw "
        f"(from the Critic) using a Socratic question. NEVER write code for them."
    )
    final_response: str = (await _ollama.generate(
        prompt=judge_prompt,
        options=_FAST_OPTS,
    )).strip()

    logger.info("\n[JUDGE]\n%s\n%s", final_response, _SEP)

    # ------------------------------------------------------------------
    # Step 5 — Assemble agent logs + persist mastery signal
    # ------------------------------------------------------------------
    agent_logs: list[str] = [
        f"[CRITIC] {critic_review}",
        f"[DEFENDER] {defender_review}",
        "[JUDGE] Consensus reached. Generating Socratic hint.",
    ]

    await repo.update_user_mastery(
        user_id=user_id,
        concept="code_review",
        score=50,
    )

    return OrchestrationResult(
        language=exec_language,
        version=exec_version,
        stdout=stdout,
        stderr=stderr,
        execution_output=execution_output,
        exit_code=exit_code,
        agent_logs=agent_logs,
        tutor_feedback=final_response,
    )
