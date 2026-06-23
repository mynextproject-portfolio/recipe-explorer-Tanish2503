"""
Tests for the versioned /api/v1/recipes endpoints.

Verifies:
- Same contract as /api/recipes (v1 compat)
- Deprecation, Sunset, and Link headers present on every response
- v2 fields absent from response bodies
"""

_DEPR_HEADER = "Deprecation"
_SUNSET_HEADER = "Sunset"
_LINK_HEADER = "Link"


def _assert_deprecation_headers(response) -> None:
    assert _DEPR_HEADER in response.headers, "Deprecation header missing"
    assert _SUNSET_HEADER in response.headers, "Sunset header missing"
    assert _LINK_HEADER in response.headers, "Link header missing"
    assert "/api/v2/recipes" in response.headers[_LINK_HEADER]


# ---------------------------------------------------------------------------
# List / search
# ---------------------------------------------------------------------------

def test_v1_get_recipes_returns_list(client, clean_storage):
    resp = client.get("/api/v1/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert "recipes" in data
    assert isinstance(data["recipes"], list)
    _assert_deprecation_headers(resp)


def test_v1_get_recipes_no_v2_fields(client, clean_storage, sample_recipe_data):
    client.post("/api/recipes", json=sample_recipe_data)
    resp = client.get("/api/v1/recipes")
    assert resp.status_code == 200
    recipe = resp.json()["recipes"][0]
    assert "difficulty" not in recipe
    assert "nutritional_info" not in recipe
    assert "dietary_restrictions" not in recipe


def test_v1_search_returns_deprecation_headers(client, clean_storage):
    resp = client.get("/api/v1/recipes/search?q=pasta")
    assert resp.status_code == 200
    _assert_deprecation_headers(resp)


def test_v1_search_filters_by_title(client, clean_storage, sample_recipe_data):
    sample_recipe_data["title"] = "Spaghetti Bolognese"
    client.post("/api/recipes", json=sample_recipe_data)
    resp = client.get("/api/v1/recipes?search=spaghetti")
    assert resp.status_code == 200
    recipes = resp.json()["recipes"]
    assert any("Spaghetti" in r["title"] for r in recipes)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_v1_create_recipe(client, clean_storage, sample_recipe_data):
    resp = client.post("/api/v1/recipes", json=sample_recipe_data)
    assert resp.status_code == 200
    recipe = resp.json()
    assert recipe["title"] == sample_recipe_data["title"]
    assert "id" in recipe
    _assert_deprecation_headers(resp)


def test_v1_get_recipe_by_id(client, clean_storage, sample_recipe_data):
    created = client.post("/api/recipes", json=sample_recipe_data).json()
    resp = client.get(f"/api/v1/recipes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    _assert_deprecation_headers(resp)


def test_v1_get_recipe_not_found(client, clean_storage):
    resp = client.get("/api/v1/recipes/nonexistent-id")
    assert resp.status_code == 404
    _assert_deprecation_headers(resp)


def test_v1_update_recipe(client, clean_storage, sample_recipe_data):
    created = client.post("/api/recipes", json=sample_recipe_data).json()
    updated_data = {**sample_recipe_data, "title": "Updated Title"}
    resp = client.put(f"/api/v1/recipes/{created['id']}", json=updated_data)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    _assert_deprecation_headers(resp)


def test_v1_delete_recipe(client, clean_storage, sample_recipe_data):
    created = client.post("/api/recipes", json=sample_recipe_data).json()
    resp = client.delete(f"/api/v1/recipes/{created['id']}")
    assert resp.status_code == 200
    _assert_deprecation_headers(resp)
    # Verify gone
    assert client.get(f"/api/v1/recipes/{created['id']}").status_code == 404


def test_v1_delete_recipe_not_found(client, clean_storage):
    resp = client.delete("/api/v1/recipes/nonexistent-id")
    assert resp.status_code == 404
    _assert_deprecation_headers(resp)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_v1_export_returns_json_array(client, clean_storage, sample_recipe_data):
    client.post("/api/recipes", json=sample_recipe_data)
    resp = client.get("/api/v1/recipes/export")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    _assert_deprecation_headers(resp)


# ---------------------------------------------------------------------------
# Consistency with /api/recipes
# ---------------------------------------------------------------------------

def test_v1_and_stable_return_same_data(client, clean_storage, sample_recipe_data):
    """v1 and the stable endpoint should return the same recipe data."""
    client.post("/api/recipes", json=sample_recipe_data)
    stable = client.get("/api/recipes").json()["recipes"]
    v1 = client.get("/api/v1/recipes").json()["recipes"]
    assert len(stable) == len(v1)
    assert stable[0]["id"] == v1[0]["id"]
    assert stable[0]["title"] == v1[0]["title"]
