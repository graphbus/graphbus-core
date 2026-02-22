"""
Negotiations REST API — CRUD for negotiation sessions, proposals, commits, feedback,
parties, messages, and Slack channel binding.

Multi-party negotiation model
──────────────────────────────
A negotiation session has:
  • an intent  (the goal — set at creation, immutable)
  • parties    (named participants: agents or humans)
  • messages   (the negotiation exchange — offers, counter-offers, signals)
  • slack binding (optional Slack channel + thread_ts for human-visible relay)

Parties are equal peers. The human is just another party.
No party is a blocker; the session advances autonomously.
"""

import uuid
import time
import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

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
    # Multi-party fields
    slack_channel: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    party_count: int = 0
    message_count: int = 0


# ── Party models ──────────────────────────────────────────────────────────────

class RegisterPartyRequest(BaseModel):
    party_id: str = Field(..., description="Unique identifier for this party within the session (e.g. 'graphbus', 'spicychai', 'human')")
    name: str = Field(..., description="Display name")
    kind: str = Field("agent", description="'agent' or 'human'")
    webhook_url: Optional[str] = Field(None, description="URL to POST new messages to (for push-based agents)")
    meta: dict = Field(default_factory=dict, description="Arbitrary metadata (model, host, etc.)")


class PartyResponse(BaseModel):
    party_id: str
    name: str
    kind: str
    webhook_url: Optional[str] = None
    meta: dict = {}
    joined_at: float


# ── Message models ────────────────────────────────────────────────────────────

class PostMessageRequest(BaseModel):
    from_party: str = Field(..., description="party_id of the sender")
    body: str = Field(..., description="Message content — offer, counter-offer, signal, etc.")
    kind: str = Field("offer", description="'offer' | 'counter' | 'accept' | 'reject' | 'signal' | 'info'")
    to_party: Optional[str] = Field(None, description="Targeted party_id, or null for broadcast")
    meta: dict = Field(default_factory=dict, description="Arbitrary metadata")


class MessageResponse(BaseModel):
    seq: int
    session_id: str
    from_party: str
    body: str
    kind: str
    to_party: Optional[str] = None
    meta: dict = {}
    timestamp: float


# ── Slack binding models ───────────────────────────────────────────────────────

class BindSlackRequest(BaseModel):
    channel: str = Field(..., description="Slack channel ID (e.g. 'C0ABCDEF')")
    thread_ts: Optional[str] = Field(None, description="Slack thread timestamp to bind to; omit to create a new thread")


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


# ── Parties ──────────────────────────────────────────────────────────────────

@router.post("/{session_id}/parties", response_model=PartyResponse, status_code=201)
async def register_party(
    session_id: str,
    req: RegisterPartyRequest,
    api_key: str = Depends(require_api_key),
):
    """Register a party (agent or human) on a negotiation session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    party = {
        "party_id": req.party_id,
        "name": req.name,
        "kind": req.kind,
        "webhook_url": req.webhook_url,
        "meta": req.meta,
        "joined_at": time.time(),
    }
    result = negotiation_store.add_party(session_id, party)
    if result is None:
        raise HTTPException(status_code=409, detail=f"Party {req.party_id!r} already registered")
    return PartyResponse(**result)


@router.get("/{session_id}/parties", response_model=list[PartyResponse])
async def list_parties(
    session_id: str,
    api_key: str = Depends(require_api_key),
):
    """List all parties registered on a session."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return [PartyResponse(**p) for p in negotiation_store.get_parties(session_id)]


@router.delete("/{session_id}/parties/{party_id}", status_code=204)
async def remove_party(
    session_id: str,
    party_id: str,
    api_key: str = Depends(require_api_key),
):
    """Remove a party from a session (they've left the negotiation)."""
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    removed = negotiation_store.remove_party(session_id, party_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Party {party_id!r} not found")


# ── Messages ─────────────────────────────────────────────────────────────────

async def _notify_parties(session_id: str, message: dict, sender_party_id: str) -> None:
    """
    Fire-and-forget: POST the new message to all parties' webhook_urls,
    except the sender. Errors are swallowed (non-blocking).
    """
    parties = negotiation_store.get_parties(session_id)
    targets = [p for p in parties if p.get("webhook_url") and p["party_id"] != sender_party_id]
    if not targets:
        return

    payload = {
        "event": "new_message",
        "session_id": session_id,
        "message": message,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            client.post(p["webhook_url"], json=payload)
            for p in targets
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for p, r in zip(targets, results):
            if isinstance(r, Exception):
                print(f"[negotiations] webhook notify failed for {p['party_id']}: {r}")


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=201)
async def post_message(
    session_id: str,
    req: PostMessageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key),
):
    """
    Post a negotiation message from a party.

    The sender is any registered party (agent or human). The message is
    stored and all other parties with webhook_urls are notified asynchronously.
    """
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    # Validate sender is a registered party (or allow unregistered for flexibility)
    party = negotiation_store.get_party(session_id, req.from_party)
    if party is None:
        raise HTTPException(
            status_code=422,
            detail=f"Party {req.from_party!r} is not registered. Register via POST /{session_id}/parties first.",
        )

    # Assign sequence number
    existing = negotiation_store.get_messages(session_id)
    seq = len(existing) + 1

    message = {
        "seq": seq,
        "session_id": session_id,
        "from_party": req.from_party,
        "body": req.body,
        "kind": req.kind,
        "to_party": req.to_party,
        "meta": req.meta,
        "timestamp": time.time(),
    }

    negotiation_store.add_message(session_id, message)

    # Notify other parties in background (non-blocking)
    background_tasks.add_task(_notify_parties, session_id, message, req.from_party)

    return MessageResponse(**message)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    since: int = 0,
    api_key: str = Depends(require_api_key),
):
    """
    List messages in a session.

    Use `since=N` to poll for new messages (returns messages with seq > N).
    """
    if negotiation_store.get_negotiation_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return [MessageResponse(**m) for m in negotiation_store.get_messages(session_id, since_seq=since)]


# ── Slack binding ─────────────────────────────────────────────────────────────

@router.post("/{session_id}/slack", response_model=SessionResponse)
async def bind_slack(
    session_id: str,
    req: BindSlackRequest,
    api_key: str = Depends(require_api_key),
):
    """
    Bind a negotiation session to a Slack channel (and optionally a specific thread).

    Once bound, the OpenClaw agent bridges messages between the GraphBus session
    and the Slack thread — posting new messages as thread replies and injecting
    Slack replies back as party messages.
    """
    session = negotiation_store.bind_slack(session_id, req.channel, req.thread_ts)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return SessionResponse(**session)
