"""
Settings API routes — user preferences, model configurations, etc.

Endpoints:
  GET    /api/settings/models       Get user's configured LLM models
  PUT    /api/settings/models       Save user's configured LLM models

Firestore schema:
  user_settings/{uid}:  models (array of ModelConfig)
"""

import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from graphbus_api.firebase_auth import get_db, verify_firebase_token, is_firebase_initialized

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


# ── Supported providers ────────────────────────────────────────────────────

SUPPORTED_PROVIDERS = {
    "anthropic": ["claude-haiku-4-5", "claude-sonnet-4-5"],
    "deepseek": ["deepseek-reasoner"],
    "openai": ["gpt-4o", "gpt-4-turbo"],
    "openrouter": ["auto"],
}


# ── Helper functions ──────────────────────────────────────────────────────

def validate_model_config(config: dict) -> bool:
    """
    Validate a model configuration.

    Returns True if valid, False otherwise.
    """
    if not isinstance(config, dict):
        return False
    
    if "provider" not in config or config["provider"] not in SUPPORTED_PROVIDERS:
        return False
    
    if "model" not in config:
        return False
    
    if "name" not in config:
        return False
    
    return True


def get_user_models(uid: str) -> list[dict]:
    """
    Get user's saved model configurations from Firestore.

    Returns list of ModelConfig dicts, or empty list if none saved.
    """
    db = get_db()
    if db is None:
        logger.warning("Firebase not initialized for get_user_models")
        return []
    
    try:
        doc = db.collection("user_settings").document(uid).get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("models", [])
        return []
    except Exception as exc:
        logger.error("Firestore error in get_user_models: %s", exc)
        return []


def save_user_models(uid: str, models: list[dict]) -> bool:
    """
    Save user's model configurations to Firestore.

    Returns True if successful, False otherwise.
    """
    db = get_db()
    if db is None:
        logger.warning("Firebase not initialized for save_user_models")
        return False
    
    # Validate all models
    for model in models:
        if not validate_model_config(model):
            logger.warning("Invalid model config: %s", model)
            return False
    
    try:
        from graphbus_api.firebase_auth import firestore
        db.collection("user_settings").document(uid).set({
            "models": models,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return True
    except Exception as exc:
        logger.error("Firestore error in save_user_models: %s", exc)
        return False


def update_user_models(uid: str, models: list[dict]) -> bool:
    """
    Update user's model configurations in Firestore.

    Returns True if successful, False otherwise.
    """
    # Validate all models
    for model in models:
        if not validate_model_config(model):
            logger.warning("Invalid model config: %s", model)
            return False
    
    db = get_db()
    if db is None:
        logger.warning("Firebase not initialized for update_user_models")
        return False
    
    try:
        from graphbus_api.firebase_auth import firestore
        db.collection("user_settings").document(uid).update({
            "models": models,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return True
    except Exception as exc:
        logger.error("Firestore error in update_user_models: %s", exc)
        return False


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelsResponse)
async def get_user_models_endpoint(x_firebase_token: str = Header(...)):
    """
    Get the user's configured LLM models.

    Authorization: Firebase ID token in x-firebase-token header.
    """
    if not is_firebase_initialized():
        logger.warning("Firebase not initialized for GET /api/settings/models")
        return ModelsResponse(models=[])
    
    try:
        claims = verify_firebase_token(x_firebase_token)
        uid = claims["uid"]
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(exc)}")
    
    models = get_user_models(uid)
    return ModelsResponse(models=models)


@router.put("/models")
async def save_user_models_endpoint(
    body: ModelsRequest,
    x_firebase_token: str = Header(...)
):
    """
    Save the user's configured LLM models.

    Authorization: Firebase ID token in x-firebase-token header.
    """
    if not is_firebase_initialized():
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        claims = verify_firebase_token(x_firebase_token)
        uid = claims["uid"]
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(exc)}")
    
    # Validate request
    if not body.models:
        logger.warning("Empty models list submitted for user %s", uid)
        return {
            "status": "error",
            "detail": "At least one model is required",
        }
    
    # Save models
    success = save_user_models(uid, [m.dict() for m in body.models])
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save models")
    
    logger.info("Saved %d models for user %s", len(body.models), uid)
    return {
        "status": "ok",
        "count": len(body.models),
    }
