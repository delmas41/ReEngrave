"""
JWT and password hashing utilities.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from core.config import settings

ALGORITHM = "HS256"

BCRYPT_ROUNDS = 12  # same cost passlib's bcrypt handler defaulted to

# bcrypt only reads the first 72 bytes; bcrypt>=5 raises on longer input where
# passlib silently truncated. Truncate here so long passphrases keep working
# and hashes made before this change still verify.
_BCRYPT_MAX_BYTES = 72


def _pw_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed / non-bcrypt stored hash: fail closed instead of 500.
        return False


def _create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
    )
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str, email: str) -> str:
    return _create_token(
        {"sub": user_id, "email": email, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """Decode and return JWT payload. Raises jose.JWTError if invalid/expired."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
