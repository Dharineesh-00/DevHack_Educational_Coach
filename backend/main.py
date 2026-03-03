import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
# CORS — allow the Vite dev server (and any localhost port) to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],   # includes OPTIONS so preflight passes
    allow_headers=["*"],
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


class SubmitResponse(BaseModel):
    # Execution details
    language: str
    version: str
    stdout: str
    stderr: str
    execution_output: str
    exit_code: int

    # Agent debate — rendered in the React agent terminal
    agent_logs: list[str]
    tutor_response: str


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
    Good Cop / Bad Cop Interview Panel:

    1. **Execute** the code via Piston and capture stdout/stderr.
    2. **Critic** (Harsh Staff Engineer) roasts the code quality / complexity.
    3. **Defender** (Empathetic DevRel Coach) counters the Critic.
    4. **Judge** (Lead Interviewer) synthesises a Socratic hint for the student.

    Returns ``agent_logs`` (the debate transcript) and ``tutor_response``
    (the Judge's final message) for the frontend agent terminal.
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
        agent_logs=result.agent_logs,
        tutor_response=result.tutor_feedback,
    )
 
