"""
auth.py — QuantAI Backend Token Verification
==============================================
Verifies Google ID tokens issued by Firebase Auth.
Every protected route calls `verify_token` as a FastAPI dependency.

SETUP:
  1. pip install firebase-admin
  2. Go to Firebase console → Project settings → Service accounts
  3. Click "Generate new private key" → save as service-account.json
  4. Set env var: GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
     OR paste the JSON contents into FIREBASE_SERVICE_ACCOUNT env var.
"""

import os
import json
from dataclasses import dataclass
from fastapi import Header, HTTPException, status

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# ──────────────────────────────────────────
#  FIREBASE ADMIN INIT  (runs once on import)
# ──────────────────────────────────────────

def _init_firebase():
    if firebase_admin._apps:
        return  # already initialised

    # Option A: JSON string in environment variable (recommended for prod / CI)
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if service_account_json:
        cred = credentials.Certificate(json.loads(service_account_json))
        firebase_admin.initialize_app(cred)
        return

    # Option B: Path to JSON file (good for local dev)
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./service-account.json")
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        return

    raise RuntimeError(
        "Firebase credentials not found.\n"
        "Set FIREBASE_SERVICE_ACCOUNT (JSON string) or "
        "GOOGLE_APPLICATION_CREDENTIALS (path to JSON file)."
    )


_init_firebase()

# ──────────────────────────────────────────
#  USER CLAIMS  (passed to route handlers)
# ──────────────────────────────────────────

@dataclass
class UserClaims:
    uid:   str          # Firebase user ID — use as database key
    email: str
    name:  str

# ──────────────────────────────────────────
#  FASTAPI DEPENDENCY
# ──────────────────────────────────────────

async def verify_token(authorization: str = Header(...)) -> UserClaims:
    """
    FastAPI dependency.  Reads the Authorization header, verifies the
    Firebase ID token, and returns a UserClaims object.

    Usage in a route:
        @app.get("/api/portfolio")
        async def portfolio(user: UserClaims = Depends(verify_token)):
            ...
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    try:
        decoded = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

    return UserClaims(
        uid   = decoded["uid"],
        email = decoded.get("email", ""),
        name  = decoded.get("name", ""),
    )
