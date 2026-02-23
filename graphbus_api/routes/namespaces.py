"""
Namespaces REST API — CRUD for user namespaces.

A namespace is a logical grouping for agents, topics, and negotiations.
Stored in Firestore under users/{uid}/namespaces/{name}.
"""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from graphbus_api.firebase_auth import (
    is_firebase_initialized,
    verify_firebase_token,
)

router = APIRouter(prefix="/namespaces", tags=["namespaces"])


# ── Request / Response models ────────────────────────────────────────────────

class CreateNamespaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


class NamespaceResponse(BaseModel):
    name: str
    created_at: float
    agent_count: int = 0
    topic_count: int = 0


# ── In-memory store (swap for Firestore in production) ───────────────────────

_namespaces: dict[str, list[dict]] = {}  # uid -> [namespace_dicts]


def _get_user_namespaces(uid: str) -> list[dict]:
    return _namespaces.get(uid, [])


def _add_namespace(uid: str, name: str) -> dict:
    if uid not in _namespaces:
        _namespaces[uid] = []
    ns = {"name": name, "created_at": time.time(), "agent_count": 0, "topic_count": 0}
    _namespaces[uid].append(ns)
    return ns


# ── Auth helper ──────────────────────────────────────────────────────────────

async def _get_uid(x_firebase_token: Optional[str] = Header(None)) -> str:
    if not x_firebase_token:
        raise HTTPException(status_code=401, detail="Missing X-Firebase-Token header")
    if not is_firebase_initialized():
        raise HTTPException(status_code=503, detail="Firebase not configured")
    try:
        claims = verify_firebase_token(x_firebase_token)
        return claims["uid"]
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_namespaces(x_firebase_token: Optional[str] = Header(None)):
    """List all namespaces for the authenticated user."""
    uid = await _get_uid(x_firebase_token)
    namespaces = _get_user_namespaces(uid)
    return {"namespaces": namespaces}


@router.post("", status_code=201)
async def create_namespace(
    req: CreateNamespaceRequest,
    x_firebase_token: Optional[str] = Header(None),
):
    """Create a new namespace."""
    uid = await _get_uid(x_firebase_token)
    existing = _get_user_namespaces(uid)
    if any(ns["name"] == req.name for ns in existing):
        raise HTTPException(status_code=409, detail="Namespace already exists")
    ns = _add_namespace(uid, req.name)
    return ns


@router.get("/{name}")
async def get_namespace(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Get a specific namespace."""
    uid = await _get_uid(x_firebase_token)
    namespaces = _get_user_namespaces(uid)
    ns = next((n for n in namespaces if n["name"] == name), None)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    return ns


@router.delete("/{name}", status_code=204)
async def delete_namespace(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Delete a namespace."""
    uid = await _get_uid(x_firebase_token)
    namespaces = _get_user_namespaces(uid)
    ns = next((n for n in namespaces if n["name"] == name), None)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    _namespaces[uid] = [n for n in namespaces if n["name"] != name]


@router.get("/{name}/topology")
async def get_namespace_topology(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Get the agent topology for a namespace."""
    uid = await _get_uid(x_firebase_token)
    namespaces = _get_user_namespaces(uid)
    ns = next((n for n in namespaces if n["name"] == name), None)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    # TODO: return real topology from build artifacts
    return {"agents": [], "topics": [], "edges": []}
