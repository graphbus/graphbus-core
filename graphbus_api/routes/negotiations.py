"""
Negotiations REST API — CRUD for negotiation sessions, proposals, commits, and feedback.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from graphbus_api.auth import require_api_key
from graphbus_api.store import negotiation_store


router = APIRouter(prefix="/negotiations", tags=["negotiations"])


# ── Request / Response models ────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    intent: str


class UpdateSessionRequest(BaseModel):
    status: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    modified_files: Optional[list[str]] = None


class FeedbackRequest(BaseModel):
    author: str
    body: str


class SessionResponse(BaseModel):
    session_id: str
    intent: str
    status: str
    timestamp: float
    branch_name: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    modified_files: list[str] = []
    commit_count: int = 0
    developer_feedback: list[dict] = []
    created_at: float


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    req: CreateSessionRequest,
    api_key: str = Depends(require_api_key),
):
    """Create a new negotiation session."""
    session_id = f"negotiate_{uuid.uuid4().hex[:8]}"
    branch_slug = req.intent.lower().replace(" ", "-")[:50]
    branch_name = f"graphbus/negotiate-{branch_slug}-{uuid.uuid4().hex[:6]}"

    session = negotiation_store.create_negotiation_session(
        session_id=session_id,
        intent=req.intent,
        branch_name=branch_name,
    )
    return SessionResponse(**session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    status: Optional[str] = None,
    api_key: str = Depends(require_api_key),
):
    """List all negotiation sessions, optionally filtered by status."""
    sessions = negotiation_store.list_negotiation_sessions(status=status)
    return [SessionResponse(**s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    api_key: str = Depends(require_api_key),
):
    """Get a single negotiation session."""
    session = negotiation_store.get_negotiation_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return SessionResponse(**session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    req: UpdateSessionRequest,
    api_key: str = Depends(require_api_key),
):
    """Update fields on an existing negotiation session."""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    session = negotiation_store.update_negotiation_session(session_id, updates)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return SessionResponse(**session)


# ── Proposals ────────────────────────────────────────────────────────────────

@router.post("/{session_id}/proposals", status_code=201)
async def add_proposal(
    session_id: str,
    proposal: dict,
    api_key: str = Depends(require_api_key),
):
    """Add a proposal to a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    negotiation_store.add_proposal(session_id, proposal)
    return {"status": "ok"}


@router.get("/{session_id}/proposals")
async def get_proposals(
    session_id: str,
    api_key: str = Depends(require_api_key),
):
    """List all proposals for a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return negotiation_store.get_proposals(session_id)


# ── Commits ──────────────────────────────────────────────────────────────────

@router.post("/{session_id}/commits", status_code=201)
async def add_commit(
    session_id: str,
    commit_record: dict,
    api_key: str = Depends(require_api_key),
):
    """Add a commit record to a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    negotiation_store.add_commit(session_id, commit_record)
    return {"status": "ok"}


@router.get("/{session_id}/commits")
async def get_commits(
    session_id: str,
    api_key: str = Depends(require_api_key),
):
    """List all commits for a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return negotiation_store.get_commits(session_id)


# ── Feedback ─────────────────────────────────────────────────────────────────

@router.post("/{session_id}/feedback", status_code=201)
async def add_feedback(
    session_id: str,
    req: FeedbackRequest,
    api_key: str = Depends(require_api_key),
):
    """Add developer feedback to a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    negotiation_store.add_feedback(session_id, author=req.author, body=req.body)
    return {"status": "ok"}
