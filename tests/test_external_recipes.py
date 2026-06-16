"""
Contract tests for the TheMealDB integration exposed through /api/recipes.
The adapter functions are monkeypatched so these tests never hit the real
network.
"""
from app.services import themealdb
from app.models import Recipe

EXTERNAL_RECIPE = Recipe(
    id="52772",
    title="Teriyaki Chicken Casserole",
    description="Chicken dish from Japanese",
    cuisine="Japanese",
    ingredients=["3/4 cup soy sauce"],
    instructions=["Preheat oven.", "Bake."],
    tags=["Casserole"],
    source="external",
)


def test_search_combines_internal_and_external_results(client, clean_storage, sample_recipe_data, monkeypatch):
    client.post("/api/recipes", json=sample_recipe_data)

    async def fake_search(query):
        return [EXTERNAL_RECIPE]

    monkeypatch.setattr(themealdb, "search_external_recipes", fake_search)

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200

    recipes = response.json()["recipes"]
    sources = {recipe["source"] for recipe in recipes}
    assert sources == {"internal", "external"}


def test_search_without_query_skips_external_call(client, clean_storage, monkeypatch):
    async def fake_search(query):
        raise AssertionError("external search should not be called without a search term")

    monkeypatch.setattr(themealdb, "search_external_recipes", fake_search)

    response = client.get("/api/recipes")
    assert response.status_code == 200


def test_search_degrades_gracefully_when_external_api_fails(client, clean_storage, sample_recipe_data, monkeypatch):
    client.post("/api/recipes", json=sample_recipe_data)

    async def failing_search(query):
        raise themealdb.MealDBError("TheMealDB API timed out")

    monkeypatch.setattr(themealdb, "search_external_recipes", failing_search)

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200

    body = response.json()
    assert len(body["recipes"]) == 1
    assert body["recipes"][0]["source"] == "internal"
    assert "external_search_error" in body


def test_get_external_recipe_success(client, monkeypatch):
    async def fake_get(meal_id):
        assert meal_id == "52772"
        return EXTERNAL_RECIPE

    monkeypatch.setattr(themealdb, "get_external_recipe", fake_get)

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 200
    assert response.json()["source"] == "external"
    assert response.json()["id"] == "52772"


def test_get_external_recipe_not_found(client, monkeypatch):
    async def fake_get(meal_id):
        return None

    monkeypatch.setattr(themealdb, "get_external_recipe", fake_get)

    response = client.get("/api/recipes/external/does-not-exist")
    assert response.status_code == 404


def test_get_external_recipe_upstream_failure_returns_502(client, monkeypatch):
    async def failing_get(meal_id):
        raise themealdb.MealDBError("TheMealDB API is unreachable")

    monkeypatch.setattr(themealdb, "get_external_recipe", failing_get)

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 502


def test_search_endpoint_alias_combines_both_sources(client, clean_storage, sample_recipe_data, monkeypatch):
    """GET /api/recipes/search?q= must not be swallowed by the {recipe_id} route."""
    client.post("/api/recipes", json=sample_recipe_data)

    async def fake_search(query):
        assert query == "arrabiata"
        return [EXTERNAL_RECIPE]

    monkeypatch.setattr(themealdb, "search_external_recipes", fake_search)

    response = client.get("/api/recipes/search", params={"q": "arrabiata"})
    assert response.status_code == 200

    recipes = response.json()["recipes"]
    sources = {recipe["source"] for recipe in recipes}
    assert "external" in sources


def test_search_endpoint_alias_accepts_search_param(client, clean_storage, monkeypatch):
    async def fake_search(query):
        return [EXTERNAL_RECIPE]

    monkeypatch.setattr(themealdb, "search_external_recipes", fake_search)

    response = client.get("/api/recipes/search", params={"search": "arrabiata"})
    assert response.status_code == 200
    assert len(response.json()["recipes"]) == 1


# --- HTML home page ---

def test_home_page_search_shows_external_results(client, clean_storage, sample_recipe_data, monkeypatch):
    client.post("/api/recipes", json=sample_recipe_data)

    async def fake_search(query):
        return [EXTERNAL_RECIPE]

    monkeypatch.setattr(themealdb, "search_external_recipes", fake_search)

    response = client.get("/", params={"search": "Test"})
    assert response.status_code == 200
    assert EXTERNAL_RECIPE.title in response.text
    assert "TheMealDB" in response.text


def test_home_page_search_degrades_gracefully_on_external_failure(client, clean_storage, sample_recipe_data, monkeypatch):
    client.post("/api/recipes", json=sample_recipe_data)

    async def failing_search(query):
        raise themealdb.MealDBError("TheMealDB API timed out")

    monkeypatch.setattr(themealdb, "search_external_recipes", failing_search)

    response = client.get("/", params={"search": "Test"})
    assert response.status_code == 200
    assert "TheMealDB API timed out" in response.text


def test_external_recipe_detail_page(client, monkeypatch):
    async def fake_get(meal_id):
        assert meal_id == "52772"
        return EXTERNAL_RECIPE

    monkeypatch.setattr(themealdb, "get_external_recipe", fake_get)

    response = client.get("/recipes/external/52772")
    assert response.status_code == 200
    assert EXTERNAL_RECIPE.title in response.text
    # No edit/delete actions for recipes we don't own
    assert "Edit Recipe" not in response.text


def test_external_recipe_detail_page_not_found(client, monkeypatch):
    async def fake_get(meal_id):
        return None

    monkeypatch.setattr(themealdb, "get_external_recipe", fake_get)

    response = client.get("/recipes/external/does-not-exist")
    assert response.status_code == 404
