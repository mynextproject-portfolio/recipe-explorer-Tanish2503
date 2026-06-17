"""
Validation and error-handling contract tests for Recipe Explorer API.
These tests verify schema compliance checking, meaningful error messages,
and correct HTTP status codes (400, 404, 422) for the /api/recipes endpoints.
"""

import json


# --- 422: schema validation failures ---


def test_create_recipe_missing_required_field_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data)
    del payload["title"]
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422

    body = response.json()
    assert body["detail"] == "Validation failed"
    assert any(err["field"] == "title" for err in body["errors"])


def test_create_recipe_blank_title_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data, title="   ")
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "title" for err in response.json()["errors"])


def test_create_recipe_title_too_long_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data, title="x" * 201)
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "title" for err in response.json()["errors"])


def test_create_recipe_empty_ingredients_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data, ingredients=[])
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "ingredients" for err in response.json()["errors"])


def test_create_recipe_blank_only_ingredients_returns_422(
    client, clean_storage, sample_recipe_data
):
    """Ingredients that are only whitespace are stripped, leaving an empty list."""
    payload = dict(sample_recipe_data, ingredients=["   ", ""])
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "ingredients" for err in response.json()["errors"])


def test_create_recipe_empty_instructions_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data, instructions=[])
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "instructions" for err in response.json()["errors"])


def test_create_recipe_too_many_ingredients_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(
        sample_recipe_data, ingredients=[f"ingredient {i}" for i in range(51)]
    )
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422
    assert any(err["field"] == "ingredients" for err in response.json()["errors"])


def test_create_recipe_missing_ingredients_key_returns_422(
    client, clean_storage, sample_recipe_data
):
    payload = dict(sample_recipe_data)
    del payload["ingredients"]
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 422


def test_create_recipe_without_optional_fields_succeeds(client, clean_storage):
    """tags and cuisine are optional and should default to empty."""
    payload = {
        "title": "Minimal Recipe",
        "description": "Just the essentials",
        "ingredients": ["water"],
        "instructions": ["Boil it."],
    }
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 200
    recipe = response.json()
    assert recipe["cuisine"] == ""
    assert recipe["tags"] == []


def test_update_recipe_invalid_payload_returns_422(
    client, clean_storage, sample_recipe_data
):
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    response = client.put(
        f"/api/recipes/{recipe_id}", json={**sample_recipe_data, "title": ""}
    )
    assert response.status_code == 422


# --- 404: not found ---


def test_get_nonexistent_recipe_returns_404(client, clean_storage):
    response = client.get("/api/recipes/does-not-exist")
    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


def test_update_nonexistent_recipe_returns_404(
    client, clean_storage, sample_recipe_data
):
    response = client.put("/api/recipes/does-not-exist", json=sample_recipe_data)
    assert response.status_code == 404


def test_delete_nonexistent_recipe_returns_404(client, clean_storage):
    response = client.delete("/api/recipes/does-not-exist")
    assert response.status_code == 404


def test_delete_existing_recipe_then_get_returns_404(
    client, clean_storage, sample_recipe_data
):
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/recipes/{recipe_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"

    get_response = client.get(f"/api/recipes/{recipe_id}")
    assert get_response.status_code == 404


# --- 400: bad request (import endpoint) ---


def test_import_rejects_non_json_file(client, clean_storage):
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.txt", b"not json", "text/plain")},
    )
    assert response.status_code == 400


def test_import_rejects_malformed_json(client, clean_storage):
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", b"{not valid json", "application/json")},
    )
    assert response.status_code == 400


def test_import_rejects_non_array_json(client, clean_storage):
    content = json.dumps({"not": "a list"}).encode()
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", content, "application/json")},
    )
    assert response.status_code == 400


def test_import_rejects_oversized_file(client, clean_storage):
    content = b"[" + b" " * 1_000_001 + b"]"
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", content, "application/json")},
    )
    assert response.status_code == 400


def test_import_reports_skipped_invalid_entries(
    client, clean_storage, sample_recipe_data
):
    invalid_recipe = {**sample_recipe_data, "title": ""}
    content = json.dumps([sample_recipe_data, invalid_recipe]).encode()

    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", content, "application/json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["index"] == 1
