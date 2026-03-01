"""
Build mode routes — kick off a build job, poll its status.
"""

import os
import sys
import time
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Ensure graphbus_core is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graphbus_api.store import (
    JobStatus, BuildJob,
    create_job, get_job, list_jobs
)

router = APIRouter(prefix="/build", tags=["build"])


# ── Request / Response models ────────────────────────────────────────────────

class BuildRequest(BaseModel):
    """Start a build job."""
    project_dir: str
    """Absolute path to the project directory containing agent modules."""
    root_package: str
    """Python dotted package path for the agents (e.g. 'examples.hello_graphbus.agents')."""
    user_intent: Optional[str] = None
    """Natural-language goal passed to LLM agents during negotiation."""
    enable_agents: bool = True
    """Whether to activate LLM agent negotiation (requires ANTHROPIC_API_KEY)."""
    api_key: Optional[str] = None
    """Anthropic API key. Falls back to ANTHROPIC_API_KEY env var if omitted."""


class BuildJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    project_dir: str
    user_intent: Optional[str]
    artifacts_dir: Optional[str]
    log: list[str]
    error: Optional[str]
    summary: Optional[dict]
    created_at: float
    finished_at: Optional[float]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _job_to_response(job: BuildJob) -> BuildJobResponse:
    return BuildJobResponse(
        job_id=job.job_id,
        status=job.status,
        project_dir=job.project_dir,
        user_intent=job.user_intent,
        artifacts_dir=job.artifacts_dir,
        log=job.output_log,
        error=job.error,
        summary=job.summary,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def _run_build(job: BuildJob, root_package: str, enable_agents: bool, api_key: Optional[str]):
    """Run a build in a background thread, updating job state."""
    from graphbus_core.config import BuildConfig
    from graphbus_core.build.builder import build_project

    job.status = JobStatus.RUNNING
    log = job.output_log

    try:
        artifacts_dir = os.path.join(job.project_dir, ".graphbus")

        config = BuildConfig(
            root_package=root_package,
            output_dir=artifacts_dir,
        )

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if resolved_key:
            config.llm_config = {
                "model": "claude-sonnet-4-20250514",
                "api_key": resolved_key,
            }

        log.append(f"[graphbus] Starting build: {root_package}")
        log.append(f"[graphbus] Agents active: {enable_agents and bool(resolved_key)}")
        if job.user_intent:
            config.user_intent = job.user_intent
            log.append(f"[graphbus] User intent: {job.user_intent}")

        artifacts = build_project(
            config,
            enable_agents=enable_agents and bool(resolved_key),
        )

        job.artifacts_dir = artifacts_dir
        job.summary = {
            "output_dir": artifacts.output_dir,
            "success": artifacts.success,
        }
        log.append("[graphbus] Build complete ✅")
        job.status = JobStatus.SUCCESS

    except Exception as exc:
        job.error = str(exc)
        job.status = JobStatus.FAILED
        log.append(f"[graphbus] Build failed ❌: {exc}")

    finally:
        job.finished_at = time.time()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=BuildJobResponse, status_code=202)
def start_build(req: BuildRequest):
    """
    Kick off an async build job.

    Returns a `job_id` you can poll via `GET /api/build/{job_id}`.
    The build scans your agent modules, constructs the dependency graph,
    and (if `enable_agents=true` and an API key is available) activates
    LLM agents to negotiate code improvements.
    """
    job = create_job(project_dir=req.project_dir, user_intent=req.user_intent)

    thread = threading.Thread(
        target=_run_build,
        args=(job, req.root_package, req.enable_agents, req.api_key),
        daemon=True,
    )
    thread.start()

    return _job_to_response(job)


@router.get("/{job_id}", response_model=BuildJobResponse)
def get_build_status(job_id: str):
    """Poll the status of a build job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return _job_to_response(job)


@router.get("", response_model=list[BuildJobResponse])
def list_builds():
    """List all build jobs (newest first)."""
    return [_job_to_response(j) for j in list_jobs()]
