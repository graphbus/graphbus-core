"""
Authentication & API key management routes.

Endpoints:
  POST   /auth/verify           Verify Firebase token, create user + issue key
  GET    /auth/me               Get current user info (via API key)
  GET    /auth/keys             List user's API keys (via Firebase token)
  POST   /auth/keys             Create a new API key (via Firebase token)
  DELETE /auth/keys/{key_id}    Revoke an API key (via Firebase token)
"""

import logging

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from graphbus_api.firebase_auth import (
    create_api_key,
    get_active_key_for_user,
    get_or_create_user,
    is_firebase_initialized,
    list_user_api_keys,
    revoke_api_key,
    validate_api_key,
    verify_firebase_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response models ───────────────────────────────────────────────

class VerifyRequest(BaseModel):
    id_token: str


class VerifyResponse(BaseModel):
    uid: str
    email: str
    api_key: str | None = None
    key_id: str | None = None


class MeResponse(BaseModel):
    uid: str
    email: str
    display_name: str | None = None


class CreateKeyRequest(BaseModel):
    label: str = "default"


class CreateKeyResponse(BaseModel):
    key_id: str
    api_key: str
    created_at: str | None = None


class KeyInfo(BaseModel):
    key_id: str
    label: str
    preview: str
    created_at: str | None = None
    last_used: str | None = None
    revoked: bool = False


# ── Helpers ─────────────────────────────────────────────────────────────────

def _require_firebase():
    """Raise 503 if Firebase is not initialized."""
    if not is_firebase_initialized():
        raise HTTPException(
            status_code=503,
            detail="Firebase is not configured on this server. Use env-var API key auth instead.",
        )


def _verify_token(id_token: str) -> dict:
    """Verify a Firebase ID token, raising 401 on failure."""
    try:
        return verify_firebase_token(id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/verify", response_model=VerifyResponse)
async def auth_verify(body: VerifyRequest):
    """
    Verify a Firebase ID token, create the user if new, and return an API key.

    On first login an API key is automatically created. Subsequent logins
    return the existing active key (or create a new one if all are revoked).
    """
    _require_firebase()

    claims = _verify_token(body.id_token)
    uid = claims["uid"]
    email = claims.get("email", "")
    display_name = claims.get("name")

    try:
        get_or_create_user(uid, email, display_name)
    except Exception as exc:
        logger.error("Failed to get/create user: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create user record") from exc

    # Check for an existing active key
    existing = get_active_key_for_user(uid)
    if existing:
        return VerifyResponse(
            uid=uid,
            email=email,
            api_key=None,  # never re-expose plaintext
            key_id=existing["key_id"],
        )

    # No active key — create one
    try:
        key_id, plaintext = create_api_key(uid, label="default")
        return VerifyResponse(uid=uid, email=email, api_key=plaintext, key_id=key_id)
    except Exception as exc:
        logger.error("Failed to create API key: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create API key") from exc


@router.get("/me", response_model=MeResponse)
async def auth_me(x_api_key: str = Header(...)):
    """
    Get the current user's profile using their API key.
    """
    _require_firebase()

    user = validate_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return MeResponse(
        uid=user["uid"],
        email=user["email"],
        display_name=user.get("display_name"),
    )


@router.get("/keys", response_model=list[KeyInfo])
async def auth_list_keys(x_firebase_token: str = Header(...)):
    """
    List all API keys for the authenticated user.
    """
    _require_firebase()

    claims = _verify_token(x_firebase_token)
    uid = claims["uid"]

    try:
        keys = list_user_api_keys(uid)
    except Exception as exc:
        logger.error("Failed to list keys: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list API keys") from exc

    return [
        KeyInfo(
            key_id=k["key_id"],
            label=k["label"],
            preview=k["preview"],
            created_at=str(k["created_at"]) if k.get("created_at") else None,
            last_used=str(k["last_used"]) if k.get("last_used") else None,
            revoked=k.get("revoked", False),
        )
        for k in keys
    ]


@router.post("/keys", response_model=CreateKeyResponse)
async def auth_create_key(body: CreateKeyRequest, x_firebase_token: str = Header(...)):
    """
    Create a new API key. The plaintext key is returned only once.
    """
    _require_firebase()

    claims = _verify_token(x_firebase_token)
    uid = claims["uid"]

    try:
        key_id, plaintext = create_api_key(uid, label=body.label)
        return CreateKeyResponse(key_id=key_id, api_key=plaintext)
    except Exception as exc:
        logger.error("Failed to create key: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create API key") from exc


@router.delete("/keys/{key_id}", status_code=204)
async def auth_revoke_key(key_id: str, x_firebase_token: str = Header(...)):
    """
    Revoke an API key. Returns 204 on success.
    """
    _require_firebase()

    claims = _verify_token(x_firebase_token)
    uid = claims["uid"]

    success = revoke_api_key(uid, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found or not owned by you")

    return Response(status_code=204)
