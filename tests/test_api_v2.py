"""
Tests for the /api/v2/recipes endpoints.

Covers:
- v2 schema: difficulty, nutritional info, dietary restrictions, equipment, techniques
- Enhanced search: text, cuisine, difficulty, dietary filters + sort
- Bulk GET via ?ids= param
- Bulk create via POST /bulk
- 201 status on create
- No deprecation headers (v2 is the current version)
- Backward read: recipes created via v1 are visible in v2 with null v2 fields
"""


def test_v2_no_deprecation_headers(client, clean_storage_v2, sample_recipe_data_v2):
    resp = client.post("/api/v2/recipes", json=sample_recipe_data_v2)
    assert resp.status_code == 201
    assert "Deprecation" not in resp.headers
    assert "Sunset" not in resp.headers


# ---------------------------------------------------------------------------
# CRUD with v2 schema
# ---------------------------------------------------------------------------

def test_v2_create_recipe_returns_201(client, clean_storage_v2, sample_recipe_data_v2):
    resp = client.post("/api/v2/recipes", json=sample_recipe_data_v2)
    assert resp.status_code == 201
    recipe = resp.json()
    assert "id" in recipe
    assert recipe["difficulty"] == "beginner"
    assert recipe["prep_time_minutes"] == 10
    assert recipe["cook_time_minutes"] == 20
    assert recipe["servings"] == 4
    assert recipe["nutritional_info"]["calories"] == 380
    assert "vegan" in recipe["dietary_restrictions"]
    assert "dairy_free" in recipe["dietary_restrictions"]
    assert "pot" in recipe["equipment"]
    assert "boiling" in recipe["techniques"]


def test_v2_create_recipe_minimal(client, clean_storage_v2, sample_recipe_data):
    """A v1-schema payload is valid for the v2 endpoint; v2 fields default to null/[]."""
    resp = client.post("/api/v2/recipes", json=sample_recipe_data)
    assert resp.status_code == 201
    recipe = resp.json()
    assert recipe["difficulty"] is None
    assert recipe["dietary_restrictions"] == []
    assert recipe["equipment"] == []
    assert recipe["nutritional_info"] is None


def test_v2_get_recipe_by_id_has_v2_fields(client, clean_storage_v2, sample_recipe_data_v2):
    created = client.post("/api/v2/recipes", json=sample_recipe_data_v2).json()
    resp = client.get(f"/api/v2/recipes/{created['id']}")
    assert resp.status_code == 200
    r = resp.json()
    assert r["difficulty"] == "beginner"
    assert r["nutritional_info"]["calories"] == 380


def test_v2_get_recipe_not_found(client, clean_storage_v2):
    resp = client.get("/api/v2/recipes/does-not-exist")
    assert resp.status_code == 404


def test_v2_update_recipe(client, clean_storage_v2, sample_recipe_data_v2):
    created = client.post("/api/v2/recipes", json=sample_recipe_data_v2).json()
    patch = {**sample_recipe_data_v2, "difficulty": "advanced", "servings": 8}
    resp = client.put(f"/api/v2/recipes/{created['id']}", json=patch)
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == "advanced"
    assert resp.json()["servings"] == 8


def test_v2_update_recipe_not_found(client, clean_storage_v2, sample_recipe_data_v2):
    resp = client.put("/api/v2/recipes/nonexistent", json=sample_recipe_data_v2)
    assert resp.status_code == 404


def test_v2_delete_recipe(client, clean_storage_v2, sample_recipe_data_v2):
    created = client.post("/api/v2/recipes", json=sample_recipe_data_v2).json()
    resp = client.delete(f"/api/v2/recipes/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/v2/recipes/{created['id']}").status_code == 404


def test_v2_delete_recipe_not_found(client, clean_storage_v2):
    assert client.delete("/api/v2/recipes/nonexistent").status_code == 404


# ---------------------------------------------------------------------------
# Enhanced search: filters
# ---------------------------------------------------------------------------

def test_v2_search_by_text(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)
    resp = client.get("/api/v2/recipes?search=pasta")
    assert resp.status_code == 200
    recipes = resp.json()["recipes"]
    assert any("Pasta" in r["title"] or "pasta" in r.get("tags", []) for r in recipes)


def test_v2_search_no_match(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)
    resp = client.get("/api/v2/recipes?search=sushi")
    assert resp.status_code == 200
    assert len(resp.json()["recipes"]) == 0


def test_v2_filter_by_cuisine(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)  # Italian
    other = {**sample_recipe_data_v2, "title": "Tacos", "cuisine": "Mexican"}
    client.post("/api/v2/recipes", json=other)

    resp = client.get("/api/v2/recipes?cuisine=Italian")
    assert resp.status_code == 200
    results = resp.json()["recipes"]
    assert all(r["cuisine"].lower() == "italian" for r in results)


def test_v2_filter_by_difficulty(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)  # beginner
    hard = {**sample_recipe_data_v2, "title": "Beef Wellington", "difficulty": "expert"}
    client.post("/api/v2/recipes", json=hard)

    resp = client.get("/api/v2/recipes?difficulty=expert")
    assert resp.status_code == 200
    results = resp.json()["recipes"]
    assert all(r["difficulty"] == "expert" for r in results)
    assert any(r["title"] == "Beef Wellington" for r in results)


def test_v2_filter_by_dietary(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)  # vegan
    meat = {**sample_recipe_data_v2, "title": "Burger", "dietary_restrictions": []}
    client.post("/api/v2/recipes", json=meat)

    resp = client.get("/api/v2/recipes?dietary=vegan")
    assert resp.status_code == 200
    results = resp.json()["recipes"]
    assert all("vegan" in r["dietary_restrictions"] for r in results)
    assert not any(r["title"] == "Burger" for r in results)


def test_v2_combined_filters(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)  # Italian, beginner, vegan
    # Same cuisine but not vegan
    non_vegan = {**sample_recipe_data_v2, "title": "Carbonara", "dietary_restrictions": ["dairy_free"]}
    client.post("/api/v2/recipes", json=non_vegan)

    resp = client.get("/api/v2/recipes?cuisine=Italian&dietary=vegan")
    assert resp.status_code == 200
    results = resp.json()["recipes"]
    assert all("vegan" in r["dietary_restrictions"] for r in results)
    assert not any(r["title"] == "Carbonara" for r in results)


# ---------------------------------------------------------------------------
# Enhanced search: sorting
# ---------------------------------------------------------------------------

def test_v2_sort_by_title_asc(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Zucchini Soup"})
    client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Apple Crumble"})
    resp = client.get("/api/v2/recipes?sort=title_asc")
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()["recipes"]]
    assert titles == sorted(titles, key=str.lower)


def test_v2_sort_by_title_desc(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Apple Crumble"})
    client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Zucchini Soup"})
    resp = client.get("/api/v2/recipes?sort=title_desc")
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()["recipes"]]
    assert titles == sorted(titles, key=str.lower, reverse=True)


# ---------------------------------------------------------------------------
# Bulk GET via ?ids=
# ---------------------------------------------------------------------------

def test_v2_bulk_get_by_ids(client, clean_storage_v2, sample_recipe_data_v2):
    r1 = client.post("/api/v2/recipes", json=sample_recipe_data_v2).json()
    r2 = client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Recipe B"}).json()
    r3 = client.post("/api/v2/recipes", json={**sample_recipe_data_v2, "title": "Recipe C"}).json()

    resp = client.get(f"/api/v2/recipes?ids={r1['id']},{r3['id']}")
    assert resp.status_code == 200
    returned_ids = {r["id"] for r in resp.json()["recipes"]}
    assert returned_ids == {r1["id"], r3["id"]}
    assert r2["id"] not in returned_ids


def test_v2_bulk_get_unknown_ids_ignored(client, clean_storage_v2):
    resp = client.get("/api/v2/recipes?ids=nonexistent-1,nonexistent-2")
    assert resp.status_code == 200
    assert resp.json()["recipes"] == []


# ---------------------------------------------------------------------------
# Bulk create
# ---------------------------------------------------------------------------

def test_v2_bulk_create_returns_201(client, clean_storage_v2, sample_recipe_data_v2):
    body = {"recipes": [sample_recipe_data_v2, {**sample_recipe_data_v2, "title": "Recipe 2"}]}
    resp = client.post("/api/v2/recipes/bulk", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_requested"] == 2
    assert len(data["created"]) == 2
    assert data["errors"] == []


def test_v2_bulk_create_all_have_ids(client, clean_storage_v2, sample_recipe_data_v2):
    body = {"recipes": [
        sample_recipe_data_v2,
        {**sample_recipe_data_v2, "title": "Recipe 2"},
        {**sample_recipe_data_v2, "title": "Recipe 3"},
    ]}
    resp = client.post("/api/v2/recipes/bulk", json=body)
    assert resp.status_code == 201
    created = resp.json()["created"]
    assert all("id" in r for r in created)
    assert len({r["id"] for r in created}) == 3  # all unique


def test_v2_bulk_create_empty_body_fails(client, clean_storage_v2):
    resp = client.post("/api/v2/recipes/bulk", json={"recipes": []})
    assert resp.status_code == 422


def test_v2_bulk_create_persisted(client, clean_storage_v2, sample_recipe_data_v2):
    body = {"recipes": [sample_recipe_data_v2, {**sample_recipe_data_v2, "title": "Recipe 2"}]}
    client.post("/api/v2/recipes/bulk", json=body)
    all_resp = client.get("/api/v2/recipes").json()["recipes"]
    assert len(all_resp) == 2


# ---------------------------------------------------------------------------
# Backward compat: v1-created recipe visible in v2 with null extras
# ---------------------------------------------------------------------------

def test_v1_recipes_visible_in_v2(client, clean_storage_v2, sample_recipe_data):
    """A recipe created via the v1 endpoint appears in v2 with null v2 fields."""
    client.post("/api/recipes", json=sample_recipe_data)
    resp = client.get("/api/v2/recipes")
    assert resp.status_code == 200
    recipes = resp.json()["recipes"]
    assert len(recipes) == 1
    r = recipes[0]
    assert r["difficulty"] is None
    assert r["nutritional_info"] is None
    assert r["dietary_restrictions"] == []


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_v2_export(client, clean_storage_v2, sample_recipe_data_v2):
    client.post("/api/v2/recipes", json=sample_recipe_data_v2)
    resp = client.get("/api/v2/recipes/export")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["difficulty"] == "beginner"
