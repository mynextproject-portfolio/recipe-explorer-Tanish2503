"""
Pure auth functions: password hashing and JWT encode/decode.
No I/O — fully unit-testable without a database or HTTP layer.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def _get_secret_key() -> str:
    key = os.getenv("SECRET_KEY")
    if not key:
        key = secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY env var not set — using an ephemeral key. "
            "All tokens will be invalidated on restart."
        )
    return key


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def create_access_token(user_id: str, email: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "username": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=TOKEN_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Return the decoded payload dict, or None if invalid/expired."""
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[TOKEN_ALGORITHM])
    except JWTError:
        return None
