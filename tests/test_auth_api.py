"""
Integration tests for auth API endpoints.
Uses FakeUserStorage via dependency_overrides — no real DB touched.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-integration-tests")

from app.dependencies import get_user_store
from app.main import app
from app.services.fake_user_storage import FakeUserStorage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fake_users():
    store = FakeUserStorage()
    app.dependency_overrides[get_user_store] = lambda: store
    yield store
    app.dependency_overrides.pop(get_user_store, None)


REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "username": "alice123",
    "password": "securepassword1",
}


def _register(client, payload=None) -> dict:
    resp = client.post("/api/auth/register", json=payload or REGISTER_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def test_register_returns_token_and_user(client):
    data = _register(client)
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["username"] == "alice123"
    assert "id" in data["user"]


def test_register_duplicate_email_returns_409(client):
    _register(client)
    resp = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 409


def test_register_duplicate_username_returns_409(client):
    _register(client)
    resp = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "email": "other@example.com"},
    )
    assert resp.status_code == 409


def test_register_short_password_returns_422(client):
    resp = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "password": "short"},
    )
    assert resp.status_code == 422


def test_register_invalid_email_returns_422(client):
    resp = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "email": "not-an-email"},
    )
    assert resp.status_code == 422


def test_register_invalid_username_returns_422(client):
    resp = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "username": "bad username!"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_returns_token(client):
    _register(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "securepassword1"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_returns_401(client):
    _register(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


def test_me_returns_current_user(client):
    token = _register(client)["access_token"]
    resp = client.get("/api/auth/me", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_me_without_token_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


def test_add_and_list_favorites(client):
    token = _register(client)["access_token"]
    headers = _auth_header(token)

    resp = client.post("/api/auth/favorites/recipe-abc?source=internal", headers=headers)
    assert resp.status_code == 201
    assert resp.json()["recipe_id"] == "recipe-abc"

    resp = client.get("/api/auth/favorites", headers=headers)
    assert resp.status_code == 200
    ids = [f["recipe_id"] for f in resp.json()]
    assert "recipe-abc" in ids


def test_add_duplicate_favorite_returns_409(client):
    token = _register(client)["access_token"]
    headers = _auth_header(token)
    client.post("/api/auth/favorites/recipe-abc?source=internal", headers=headers)
    resp = client.post("/api/auth/favorites/recipe-abc?source=internal", headers=headers)
    assert resp.status_code == 409


def test_same_recipe_internal_and_external_are_distinct(client):
    token = _register(client)["access_token"]
    headers = _auth_header(token)
    r1 = client.post("/api/auth/favorites/meal-1?source=internal", headers=headers)
    r2 = client.post("/api/auth/favorites/meal-1?source=external", headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201


def test_remove_favorite(client):
    token = _register(client)["access_token"]
    headers = _auth_header(token)
    client.post("/api/auth/favorites/recipe-abc?source=internal", headers=headers)

    resp = client.delete("/api/auth/favorites/recipe-abc?source=internal", headers=headers)
    assert resp.status_code == 204

    resp = client.get("/api/auth/favorites", headers=headers)
    assert resp.json() == []


def test_remove_nonexistent_favorite_returns_404(client):
    token = _register(client)["access_token"]
    resp = client.delete(
        "/api/auth/favorites/ghost?source=internal",
        headers=_auth_header(token),
    )
    assert resp.status_code == 404


def test_favorites_require_auth(client):
    assert client.get("/api/auth/favorites").status_code == 401
    assert client.post("/api/auth/favorites/x?source=internal").status_code == 401
    assert client.delete("/api/auth/favorites/x?source=internal").status_code == 401
