"""Password hashing (PBKDF2 — matches existing accounts) and JWT helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


PBKDF_SALT_LENGTH = 16
PBKDF_ITERATIONS = 120_000
PBKDF_ALGORITHM = "sha256"


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        PBKDF_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF_ITERATIONS,
    )


def hash_password(password: str) -> str:
    """Return a salted PBKDF2-HMAC-SHA256 hash, encoded as `salt_b64:key_b64`."""
    salt = os.urandom(PBKDF_SALT_LENGTH)
    key = _derive_key(password, salt)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(key).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_b64, key_b64 = stored_hash.split(":")
    except ValueError:
        return False

    try:
        salt = base64.b64decode(salt_b64)
        key = base64.b64decode(key_b64)
    except (base64.binascii.Error, ValueError):
        return False

    new_key = _derive_key(password, salt)
    return hmac.compare_digest(new_key, key)


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Sign a JWT for the given user identifier."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a JWT and return its payload. Raises JWTError on invalid tokens."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
    "JWTError",
]
