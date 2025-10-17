"""Authentication helpers: password hashing and verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Tuple

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
    """Return a salted PBKDF2 hash for the provided password."""
    salt = os.urandom(PBKDF_SALT_LENGTH)
    key = _derive_key(password, salt)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(key).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check that password matches the stored PBKDF2 hash."""
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


def extract_hash_parts(stored_hash: str) -> Tuple[str, str]:
    """Split a stored hash into salt and key (base64). Mainly for debugging."""
    salt_b64, key_b64 = stored_hash.split(":")
    return salt_b64, key_b64
