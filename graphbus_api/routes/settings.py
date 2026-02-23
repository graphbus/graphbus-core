"""
Settings API routes — user preferences, model configurations, etc.

Endpoints:
  GET    /api/settings/models       Get user's configured LLM models
  PUT    /api/settings/models       Save user's configured LLM models
"""

import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


# ── Request / Response models ───────────────────────────────────────────────

class ModelConfig(BaseModel):
    name: str
    provider: str
    model: str
    base_url: str | None = None


class ModelsRequest(BaseModel):
    models: list[ModelConfig]


class ModelsResponse(BaseModel):
    models: list[ModelConfig]


# ── In-memory storage (replace with database in production) ───────────────

# Simple in-memory storage: uid -> list of models
user_models_store = {}


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelsResponse)
async def get_user_models(x_firebase_token: str = Header(...)):
    """
    Get the user's configured LLM models.

    Authorization: Firebase ID token in x-firebase-token header.
    """
    # In a real implementation, verify the token and extract the UID
    # For now, use a placeholder UID derived from token
    uid = f"user_{hash(x_firebase_token) % 10000}"

    models = user_models_store.get(uid, [])
    return ModelsResponse(models=models)


@router.put("/models")
async def save_user_models(
    body: ModelsRequest,
    x_firebase_token: str = Header(...)
):
    """
    Save the user's configured LLM models.

    Authorization: Firebase ID token in x-firebase-token header.
    """
    # In a real implementation, verify the token and extract the UID
    uid = f"user_{hash(x_firebase_token) % 10000}"

    # Validate models
    if not body.models:
        logger.warning("Empty models list submitted for user %s", uid)

    user_models_store[uid] = body.models

    logger.info("Saved %d models for user %s", len(body.models), uid)
    return {"status": "ok", "count": len(body.models)}
