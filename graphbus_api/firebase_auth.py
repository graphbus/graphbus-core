"""
Firebase Admin SDK integration for GraphBus API.

Handles:
- Firebase initialization (graceful if not configured)
- Firebase ID token verification
- User management in Firestore
- API key creation, validation, listing, and revocation

Firestore schema:
  users/{uid}:       email, display_name, created_at, last_seen
  api_keys/{key_id}: uid, key_hash (SHA256), label, created_at, last_used, revoked
"""

import hashlib
import json
import logging
import os
import secrets
import uuid

logger = logging.getLogger(__name__)

_firebase_initialized = False
_db = None

# Lazy imports — firebase_admin is optional
firebase_admin = None
credentials = None
firebase_auth = None
firestore = None


def _import_firebase():
    """Import firebase_admin lazily so the module loads even without the package."""
    global firebase_admin, credentials, firebase_auth, firestore
    if firebase_admin is not None:
        return True
    try:
        import firebase_admin as _fa
        from firebase_admin import credentials as _cred
        from firebase_admin import auth as _auth
        from firebase_admin import firestore as _fs

        firebase_admin = _fa
        credentials = _cred
        firebase_auth = _auth
        firestore = _fs
        return True
    except ImportError:
        logger.warning("firebase-admin package not installed — Firebase features disabled")
        return False


def init_firebase() -> bool:
    """
    Initialize Firebase Admin SDK.

    Reads credentials from (in order):
      1. GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON)
      2. FIREBASE_SERVICE_ACCOUNT_JSON env var (inline JSON string)

    Returns True if initialized, False if credentials not found (graceful degradation).
    """
    global _firebase_initialized, _db

    if _firebase_initialized:
        return True

    if not _import_firebase():
        return False

    try:
        cred = None

        # Option 1: GOOGLE_APPLICATION_CREDENTIALS (file path)
        gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if gac and os.path.isfile(gac):
            cred = credentials.Certificate(gac)

        # Option 2: inline JSON
        if cred is None:
            inline_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            if inline_json:
                service_info = json.loads(inline_json)
                cred = credentials.Certificate(service_info)

        # Option 3: default path for GraphBus deployment
        if cred is None:
            default_path = os.path.expanduser("~/.config/graphbus/firebase-sa.json")
            if os.path.isfile(default_path):
                cred = credentials.Certificate(default_path)

        if cred is None:
            logger.warning(
                "No Firebase credentials found "
                "(set GOOGLE_APPLICATION_CREDENTIALS, FIREBASE_SERVICE_ACCOUNT_JSON, "
                "or place credentials at ~/.config/graphbus/firebase-sa.json). "
                "Firebase features disabled — falling back to env-var API key auth."
            )
            return False

        # GraphBus Firebase project
        project_id = os.environ.get("FIREBASE_PROJECT_ID", "graphbus-19688")
        firebase_admin.initialize_app(cred, {"projectId": project_id})

        db_name = os.environ.get("FIRESTORE_DATABASE", "(default)")
        _db = firestore.client(database_id=db_name) if db_name != "(default)" else firestore.client()
        _firebase_initialized = True

        logger.info("Firebase initialized (project=%s)", project_id)
        print(f"  ✓ Firebase: project={project_id}, Firestore ready")
        return True

    except Exception as exc:
        logger.error("Failed to initialize Firebase: %s", exc)
        return False


def get_db():
    """Return the Firestore client, or None if not initialized."""
    return _db


def is_firebase_initialized() -> bool:
    """Return whether Firebase was successfully initialized."""
    return _firebase_initialized


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.

    Returns decoded claims dict with uid, email, name, etc.
    Raises ValueError if token is invalid or Firebase is not initialized.
    """
    if not _firebase_initialized:
        raise ValueError("Firebase is not initialized")

    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except Exception as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc


def get_or_create_user(uid: str, email: str, display_name: str = None) -> dict:
    """
    Get or create a user document in Firestore users/{uid}.

    Returns the user data dict.
    """
    if not _firebase_initialized or _db is None:
        raise ValueError("Firebase is not initialized")

    try:
        user_ref = _db.collection("graphbus_users").document(uid)
        doc = user_ref.get()

        if doc.exists:
            # Update last_seen
            user_ref.update({"last_seen": firestore.SERVER_TIMESTAMP})
            return doc.to_dict()

        # Create new user
        user_data = {
            "email": email,
            "display_name": display_name,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_seen": firestore.SERVER_TIMESTAMP,
        }
        user_ref.set(user_data)
        return user_data

    except Exception as exc:
        logger.error("Firestore error in get_or_create_user: %s", exc)
        raise


def create_api_key(uid: str, label: str = "default") -> tuple[str, str]:
    """
    Create a new API key for a user.

    Returns (key_id, plaintext_key) — the plaintext is shown only once.
    Stores SHA256(key) in Firestore api_keys/{key_id}.
    """
    if not _firebase_initialized or _db is None:
        raise ValueError("Firebase is not initialized")

    plaintext = "gb_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key_id = str(uuid.uuid4())

    try:
        key_data = {
            "uid": uid,
            "key_hash": key_hash,
            "label": label,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_used": None,
            "revoked": False,
        }
        _db.collection("graphbus_api_keys").document(key_id).set(key_data)
        return key_id, plaintext

    except Exception as exc:
        logger.error("Firestore error in create_api_key: %s", exc)
        raise


def validate_api_key(api_key: str) -> dict | None:
    """
    Validate a GRAPHBUS_API_KEY against Firestore.

    Returns user info dict (uid, email, display_name) or None if invalid/revoked.
    Also updates last_used timestamp on successful validation.
    """
    if not _firebase_initialized or _db is None:
        return None

    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Query api_keys where key_hash matches
        results = (
            _db.collection("graphbus_api_keys")
            .where("key_hash", "==", key_hash)
            .where("revoked", "==", False)
            .limit(1)
            .get()
        )

        if not results:
            return None

        key_doc = results[0]
        key_data = key_doc.to_dict()

        # Update last_used
        key_doc.reference.update({"last_used": firestore.SERVER_TIMESTAMP})

        # Fetch associated user
        uid = key_data["uid"]
        user_doc = _db.collection("graphbus_users").document(uid).get()
        if not user_doc.exists:
            return None

        user_data = user_doc.to_dict()
        return {
            "uid": uid,
            "email": user_data.get("email"),
            "display_name": user_data.get("display_name"),
        }

    except Exception as exc:
        logger.error("Firestore error in validate_api_key: %s", exc)
        return None


def list_user_api_keys(uid: str) -> list[dict]:
    """
    List API keys for a user. Key values are masked — shows only prefix + last 4 chars of key_id.
    """
    if not _firebase_initialized or _db is None:
        raise ValueError("Firebase is not initialized")

    try:
        results = (
            _db.collection("graphbus_api_keys")
            .where("uid", "==", uid)
            .order_by("created_at")
            .get()
        )

        keys = []
        for doc in results:
            data = doc.to_dict()
            keys.append({
                "key_id": doc.id,
                "label": data.get("label", ""),
                "preview": f"gb_...{doc.id[-4:]}",
                "created_at": data.get("created_at"),
                "last_used": data.get("last_used"),
                "revoked": data.get("revoked", False),
            })

        return keys

    except Exception as exc:
        logger.error("Firestore error in list_user_api_keys: %s", exc)
        raise


def revoke_api_key(uid: str, key_id: str) -> bool:
    """
    Mark an API key as revoked in Firestore.

    Returns True if successfully revoked, False if key not found or not owned by uid.
    """
    if not _firebase_initialized or _db is None:
        raise ValueError("Firebase is not initialized")

    try:
        key_ref = _db.collection("graphbus_api_keys").document(key_id)
        doc = key_ref.get()

        if not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("uid") != uid:
            return False

        key_ref.update({"revoked": True})
        return True

    except Exception as exc:
        logger.error("Firestore error in revoke_api_key: %s", exc)
        return False


def get_active_key_for_user(uid: str) -> dict | None:
    """
    Get the first active (non-revoked) API key for a user.

    Returns {"key_id": ..., "label": ...} or None if no active keys.
    Note: does NOT return the plaintext key (it's never stored).
    """
    if not _firebase_initialized or _db is None:
        return None

    try:
        results = (
            _db.collection("graphbus_api_keys")
            .where("uid", "==", uid)
            .where("revoked", "==", False)
            .limit(1)
            .get()
        )

        if not results:
            return None

        doc = results[0]
        return {"key_id": doc.id, "label": doc.to_dict().get("label", "")}

    except Exception as exc:
        logger.error("Firestore error in get_active_key_for_user: %s", exc)
        return None
