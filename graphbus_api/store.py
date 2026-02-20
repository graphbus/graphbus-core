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


# ── Negotiation store ────────────────────────────────────────────────────────

class NegotiationStore:
    """In-memory store for negotiation sessions, proposals, commits, and feedback."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._proposals: dict[str, list[dict]] = {}   # session_id -> list
        self._commits: dict[str, list[dict]] = {}      # session_id -> list

    # -- sessions --

    def create_negotiation_session(self, session_id: str, intent: str, **extra: Any) -> dict:
        session = {
            "session_id": session_id,
            "intent": intent,
            "status": "in_progress",
            "timestamp": time.time(),
            "branch_name": extra.get("branch_name", ""),
            "pr_number": None,
            "pr_url": None,
            "modified_files": [],
            "commit_count": 0,
            "developer_feedback": [],
            "created_at": time.time(),
        }
        session.update(extra)
        self._sessions[session_id] = session
        self._proposals[session_id] = []
        self._commits[session_id] = []
        return session

    def get_negotiation_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def list_negotiation_sessions(self, status: Optional[str] = None) -> list[dict]:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.get("status") == status]
        return sorted(sessions, key=lambda s: s.get("created_at", 0), reverse=True)

    def update_negotiation_session(self, session_id: str, updates: dict) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.update(updates)
        return session

    # -- proposals --

    def add_proposal(self, session_id: str, proposal: dict) -> None:
        if session_id not in self._proposals:
            self._proposals[session_id] = []
        self._proposals[session_id].append(proposal)

    def get_proposals(self, session_id: str) -> list[dict]:
        return list(self._proposals.get(session_id, []))

    # -- commits --

    def add_commit(self, session_id: str, commit_record: dict) -> None:
        if session_id not in self._commits:
            self._commits[session_id] = []
        self._commits[session_id].append(commit_record)
        # bump commit_count on the session
        session = self._sessions.get(session_id)
        if session is not None:
            session["commit_count"] = len(self._commits[session_id])

    def get_commits(self, session_id: str) -> list[dict]:
        return list(self._commits.get(session_id, []))

    # -- feedback --

    def add_feedback(self, session_id: str, author: str, body: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.setdefault("developer_feedback", []).append({
            "author": author,
            "body": body,
            "timestamp": time.time(),
        })


# Singleton
negotiation_store = NegotiationStore()
