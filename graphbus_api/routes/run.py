"""
Runtime routes — start a session, call methods, publish events, get stats.
"""

import os
import sys
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graphbus_api.store import create_session, get_session, remove_session

router = APIRouter(prefix="/run", tags=["run"])


# ── Request / Response models ────────────────────────────────────────────────

class RunRequest(BaseModel):
    """Start a runtime session from build artifacts."""
    artifacts_dir: str
    """Path to the .graphbus/ directory produced by a build."""


class SessionInfo(BaseModel):
    session_id: str
    artifacts_dir: str
    nodes: list[str]
    topics: list[str]
    created_at: float


class CallRequest(BaseModel):
    node: str
    """Agent node name, e.g. 'HelloService'."""
    method: str
    """Method name decorated with @schema_method."""
    kwargs: dict[str, Any] = {}
    """Keyword arguments passed to the method."""


class PublishRequest(BaseModel):
    topic: str
    """Topic path, e.g. '/Hello/MessageGenerated'."""
    payload: dict[str, Any] = {}


class CallResponse(BaseModel):
    node: str
    method: str
    result: Any


class StatsResponse(BaseModel):
    session_id: str
    nodes_count: int
    message_bus: dict


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=SessionInfo, status_code=201)
def start_runtime(req: RunRequest):
    """
    Load build artifacts and start a runtime session.

    Returns a `session_id` for subsequent method calls and event publishing.
    """
    from graphbus_core.runtime import run_runtime

    if not os.path.isdir(req.artifacts_dir):
        raise HTTPException(status_code=400, detail=f"Artifacts dir not found: {req.artifacts_dir}")

    try:
        executor = run_runtime(req.artifacts_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    session = create_session(artifacts_dir=req.artifacts_dir, executor=executor)

    return SessionInfo(
        session_id=session.session_id,
        artifacts_dir=req.artifacts_dir,
        nodes=list(executor.nodes.keys()),
        topics=list(executor.message_bus.get_topics() if hasattr(executor.message_bus, "get_topics") else []),
        created_at=session.created_at,
    )


@router.post("/{session_id}/call", response_model=CallResponse)
def call_method(session_id: str, req: CallRequest):
    """
    Call a @schema_method on a running agent node.

    Example:
        POST /api/run/{session_id}/call
        {"node": "HelloService", "method": "generate_message", "kwargs": {"name": "World"}}
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    try:
        result = session.executor.call_method(req.node, req.method, **req.kwargs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CallResponse(node=req.node, method=req.method, result=result)


@router.post("/{session_id}/publish", status_code=204)
def publish_event(session_id: str, req: PublishRequest):
    """
    Publish an event to the message bus, triggering any @subscribe handlers.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    try:
        session.executor.publish(req.topic, req.payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{session_id}/stats", response_model=StatsResponse)
def get_stats(session_id: str):
    """Get runtime statistics for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    stats = session.executor.get_stats()
    return StatsResponse(
        session_id=session_id,
        nodes_count=stats["nodes_count"],
        message_bus=stats["message_bus"],
    )


@router.get("/{session_id}", response_model=SessionInfo)
def get_session_info(session_id: str):
    """Get info about a running session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    executor = session.executor
    return SessionInfo(
        session_id=session_id,
        artifacts_dir=session.artifacts_dir,
        nodes=list(executor.nodes.keys()),
        topics=[],
        created_at=session.created_at,
    )


@router.delete("/{session_id}", status_code=204)
def stop_session(session_id: str):
    """Stop and remove a runtime session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    try:
        session.executor.stop()
    except Exception:
        pass

    remove_session(session_id)
