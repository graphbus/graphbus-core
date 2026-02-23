"""
Namespaces REST API — CRUD for user namespaces.

Stored in Firestore: graphbus_users/{uid}/namespaces/{name}
"""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from graphbus_api.firebase_auth import (
    get_db,
    is_firebase_initialized,
    verify_firebase_token,
)

router = APIRouter(prefix="/namespaces", tags=["namespaces"])


# ── Models ───────────────────────────────────────────────────────────────────

class CreateNamespaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


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


# ── Firestore helpers ────────────────────────────────────────────────────────

def _ns_collection(uid: str):
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Firestore not available")
    return db.collection("graphbus_users").document(uid).collection("namespaces")


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_namespaces(x_firebase_token: Optional[str] = Header(None)):
    """List all namespaces for the authenticated user."""
    uid = await _get_uid(x_firebase_token)
    col = _ns_collection(uid)
    docs = col.stream()
    namespaces = []
    for doc in docs:
        data = doc.to_dict()
        data["name"] = doc.id
        namespaces.append(data)
    return {"namespaces": namespaces}


@router.post("", status_code=201)
async def create_namespace(
    req: CreateNamespaceRequest,
    x_firebase_token: Optional[str] = Header(None),
):
    """Create a new namespace."""
    uid = await _get_uid(x_firebase_token)
    col = _ns_collection(uid)
    doc_ref = col.document(req.name)
    if doc_ref.get().exists:
        raise HTTPException(status_code=409, detail="Namespace already exists")
    data = {
        "created_at": time.time(),
        "agent_count": 0,
        "topic_count": 0,
    }
    doc_ref.set(data)
    return {"name": req.name, **data}


@router.get("/{name}")
async def get_namespace(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Get a specific namespace."""
    uid = await _get_uid(x_firebase_token)
    doc = _ns_collection(uid).document(name).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Namespace not found")
    data = doc.to_dict()
    data["name"] = doc.id
    return data


@router.delete("/{name}", status_code=204)
async def delete_namespace(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Delete a namespace."""
    uid = await _get_uid(x_firebase_token)
    doc_ref = _ns_collection(uid).document(name)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Namespace not found")
    doc_ref.delete()


@router.get("/{name}/topology")
async def get_namespace_topology(name: str, x_firebase_token: Optional[str] = Header(None)):
    """Get the agent topology for a namespace."""
    uid = await _get_uid(x_firebase_token)
    doc = _ns_collection(uid).document(name).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Namespace not found")
    data = doc.to_dict()
    return {
        "agents": data.get("agents", []),
        "topics": data.get("topics", []),
        "edges": data.get("edges", []),
    }
