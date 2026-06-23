"""Unit tests for pure auth functions — no DB or HTTP needed."""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from app.services.auth import (
    TOKEN_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("correct-horse-battery")
        assert verify_password("correct-horse-battery", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-horse-battery")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_bcrypt(self):
        hashed = hash_password("any-password")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_same_password_produces_different_hashes(self):
        h1 = hash_password("password123")
        h2 = hash_password("password123")
        assert h1 != h2  # bcrypt salts are random


class TestTokenCreation:
    def test_token_contains_expected_claims(self):
        token = create_access_token("uid-1", "user@example.com", "user1")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "uid-1"
        assert payload["email"] == "user@example.com"
        assert payload["username"] == "user1"

    def test_token_has_exp_claim(self):
        token = create_access_token("uid-1", "user@example.com", "user1")
        payload = decode_access_token(token)
        assert "exp" in payload
        # Should expire roughly 24h from now
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        assert 23 < delta.total_seconds() / 3600 < 25

    def test_valid_token_decodes(self):
        token = create_access_token("uid-1", "a@b.com", "ab")
        payload = decode_access_token(token)
        assert payload is not None

    def test_invalid_token_returns_none(self):
        assert decode_access_token("not.a.valid.token") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("uid-1", "a@b.com", "ab")
        tampered = token[:-4] + "XXXX"
        assert decode_access_token(tampered) is None

    def test_expired_token_returns_none(self):
        secret = os.environ["SECRET_KEY"]
        expired_payload = {
            "sub": "uid-1",
            "email": "a@b.com",
            "username": "ab",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        }
        expired_token = jwt.encode(expired_payload, secret, algorithm=TOKEN_ALGORITHM)
        assert decode_access_token(expired_token) is None
