"""
Orchestrator — coordinates the full DSA analysis pipeline.

Pipeline
--------
1. Execute the code via Piston (get stdout/stderr).
2. Run ComplexityAgent  → structured JSON {time_complexity, space_complexity, is_optimal}.
3. Run TutorAgent       → Socratic feedback using code + execution output + complexity.

Returns an :class:`OrchestrationResult` dataclass with all intermediate
and final results so the API layer can decide what to expose.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

import httpx

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
from agents.complexity_agent import ComplexityAgent
from agents.tutor_agent import TutorAgent
from db.base_repo import MetricsRepository
from db.mock_repo import MockMetricsRepository

# Shared singletons (instantiated once at import time)
_piston = PistonClient()
_complexity_agent = ComplexityAgent()
_tutor_agent = TutorAgent()


@dataclass
class OrchestrationResult:
    """Holds every artefact produced by the pipeline."""

    # --- Piston execution ---
    language: str
    version: str
    stdout: str
    stderr: str
    execution_output: str  # combined stdout+stderr (Piston "output" field)
    exit_code: int

    # --- Complexity analysis ---
    time_complexity: str
    space_complexity: str
    is_optimal: bool

    # --- Tutor feedback ---
    tutor_feedback: str

    # Optional raw LLM response for debugging
    _complexity_raw: dict = field(default_factory=dict, repr=False)


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
    # Step 1: Execute code via Piston
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

    # ------------------------------------------------------------------
    # Step 2: Complexity analysis (can run independently of tutor)
    # ------------------------------------------------------------------
    complexity: dict = await _complexity_agent.analyze_structured(code=code)

    tc = complexity.get("time_complexity", "unknown")
    sc = complexity.get("space_complexity", "unknown")
    optimal = complexity.get("is_optimal", False)

    logger.info(
        "[AGENT: BIG-O] Analyzing code...  "
        "Time Complexity is %s  |  Space Complexity is %s  |  Optimal: %s",
        tc, sc, optimal,
    )

    # Vibe check — track failures and log emotional signal
    failure_count = _record_failure(user_id) if exit_code != 0 else 0
    logger.info("[AGENT: VIBE]  user_id=%s  |  %s", user_id, _vibe(failure_count))

    # ------------------------------------------------------------------
    # Step 3: Tutor feedback — uses code + execution output + complexity
    # ------------------------------------------------------------------
    context = TutorAgent.build_context(
        code=code,
        execution_output=execution_output,
        complexity=complexity,
    )
    is_optimal_flag = bool(complexity.get("is_optimal", False))
    constraint = "Solution is optimal — reinforce the approach." if is_optimal_flag \
        else "Be encouraging, do not give the answer."
    logger.info("[AGENT: TUTOR] Drafting response. Constraint applied: %s", constraint)

    tutor_feedback = await _tutor_agent.analyze(
        context=context,
        user_prompt=(
            "Based on the code, its output, and the complexity analysis above, "
            "provide Socratic feedback to guide the candidate."
        ),
    )

    logger.info(
        "\n%s\n[AGENT: TUTOR] Response for user_id=%s\n%s\n%s",
        _SEP, user_id, tutor_feedback.strip(), _SEP,
    )

    result = OrchestrationResult(
        language=exec_language,
        version=exec_version,
        stdout=stdout,
        stderr=stderr,
        execution_output=execution_output,
        exit_code=exit_code,
        time_complexity=tc,
        space_complexity=sc,
        is_optimal=bool(optimal),
        tutor_feedback=tutor_feedback,
        _complexity_raw=complexity,
    )

    # ------------------------------------------------------------------
    # Step 4: Persist mastery signal
    # Derive the concept from the dominant time-complexity tier so the
    # repository receives a meaningful key even without NLP tagging.
    # ------------------------------------------------------------------
    await repo.update_user_mastery(
        user_id=user_id,
        concept=result.time_complexity,
        score=100 if result.is_optimal else 50,
    )

    return result
