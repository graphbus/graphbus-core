"""
In-memory store for build jobs and runtime sessions.
In production, swap for Redis or a DB.
"""

import uuid
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BuildJob:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    project_dir: str = ""
    user_intent: Optional[str] = None
    artifacts_dir: Optional[str] = None
    output_log: list[str] = field(default_factory=list)
    error: Optional[str] = None
    summary: Optional[dict] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


@dataclass
class RuntimeSession:
    session_id: str
    artifacts_dir: str
    executor: Any  # RuntimeExecutor — avoid circular import
    created_at: float = field(default_factory=time.time)


# ── Singletons ──────────────────────────────────────────────────────────────

_build_jobs: dict[str, BuildJob] = {}
_runtime_sessions: dict[str, RuntimeSession] = {}


# ── Build jobs ───────────────────────────────────────────────────────────────

def create_job(project_dir: str, user_intent: Optional[str] = None) -> BuildJob:
    job_id = str(uuid.uuid4())
    job = BuildJob(job_id=job_id, project_dir=project_dir, user_intent=user_intent)
    _build_jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[BuildJob]:
    return _build_jobs.get(job_id)


def list_jobs() -> list[BuildJob]:
    return sorted(_build_jobs.values(), key=lambda j: j.created_at, reverse=True)


# ── Runtime sessions ─────────────────────────────────────────────────────────

def create_session(artifacts_dir: str, executor: Any) -> RuntimeSession:
    session_id = str(uuid.uuid4())
    session = RuntimeSession(session_id=session_id, artifacts_dir=artifacts_dir, executor=executor)
    _runtime_sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[RuntimeSession]:
    return _runtime_sessions.get(session_id)


def remove_session(session_id: str) -> bool:
    return _runtime_sessions.pop(session_id, None) is not None
