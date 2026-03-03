import logging

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import httpx

import orchestrator

# ------------------------------------------------------------------
# Logging — prints agent discussion to the uvicorn terminal.
# Change level to logging.WARNING (or remove) when no longer needed.
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s%(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="DSA Tutor API",
    description=(
        "Submit Python code for execution, automated complexity analysis, "
        "and Socratic tutoring feedback powered by a local LLM."
    ),
    version="2.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CodeRequest(BaseModel):
    language: str = Field(
        default="python",
        min_length=1,
        description="Programming language identifier supported by Piston (e.g. 'python').",
        examples=["python"],
    )
    code: str = Field(
        ...,
        min_length=1,
        description="Source code to execute and analyse.",
        examples=["def add(a, b):\n    return a + b\nprint(add(1, 2))"],
    )
    user_id: str = Field(
        default="anonymous",
        min_length=1,
        description="Learner identifier used to track mastery progress.",
        examples=["user_42"],
    )


class ComplexityResult(BaseModel):
    time_complexity: str
    space_complexity: str
    is_optimal: bool


class SubmitResponse(BaseModel):
    # Execution details
    language: str
    version: str
    stdout: str
    stderr: str
    execution_output: str
    exit_code: int

    # Complexity analysis
    complexity: ComplexityResult

    # Tutor feedback
    tutor_feedback: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post(
    "/submit",
    response_model=SubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit code for execution, analysis, and tutoring",
)
async def submit_code(payload: CodeRequest) -> SubmitResponse:
    """
    Full DSA pipeline:

    1. **Execute** the code via Piston and capture stdout/stderr.
    2. **Analyse** time/space complexity with a local LLM (ComplexityAgent).
    3. **Tutor** the candidate with Socratic questions (TutorAgent).

    - **language**: Piston language tag (default: `python`)
    - **code**: source code to run and analyse
    """
    try:
        result = await orchestrator.run(
            code=payload.code,
            language=payload.language,
            user_id=payload.user_id,
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="A downstream service (Piston or Ollama) timed out. Please try again.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Downstream service error: HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach a downstream service: {exc}",
        )

    return SubmitResponse(
        language=result.language,
        version=result.version,
        stdout=result.stdout,
        stderr=result.stderr,
        execution_output=result.execution_output,
        exit_code=result.exit_code,
        complexity=ComplexityResult(
            time_complexity=result.time_complexity,
            space_complexity=result.space_complexity,
            is_optimal=result.is_optimal,
        ),
        tutor_feedback=result.tutor_feedback,
    )
 
