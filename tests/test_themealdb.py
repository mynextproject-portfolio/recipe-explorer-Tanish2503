"""
Unit tests for the TheMealDB adapter. All HTTP calls are mocked via
httpx.MockTransport so these tests never hit the real network.
"""
import httpx
import pytest

from app.services import themealdb

SAMPLE_MEAL = {
    "idMeal": "52772",
    "strMeal": "Teriyaki Chicken Casserole",
    "strCategory": "Chicken",
    "strArea": "Japanese",
    "strInstructions": "Preheat oven to 350F.\r\nMix sauce ingredients.\r\nBake for 30 minutes.",
    "strTags": "Meat,Casserole",
    "strIngredient1": "soy sauce",
    "strMeasure1": "3/4 cup",
    "strIngredient2": "water",
    "strMeasure2": "1/2 cup",
    "strIngredient3": "",
    "strMeasure3": "",
}


def _client_for(handler):
    def factory():
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=themealdb.MEALDB_BASE_URL,
            timeout=themealdb.REQUEST_TIMEOUT,
        )
    return factory


def test_to_recipe_transforms_mealdb_format():
    recipe = themealdb._to_recipe(SAMPLE_MEAL)

    assert recipe.id == "52772"
    assert recipe.title == "Teriyaki Chicken Casserole"
    assert recipe.source == "external"
    assert recipe.cuisine == "Japanese"
    assert recipe.ingredients == ["3/4 cup soy sauce", "1/2 cup water"]
    assert recipe.instructions == [
        "Preheat oven to 350F.",
        "Mix sauce ingredients.",
        "Bake for 30 minutes.",
    ]
    assert "Casserole" in recipe.tags
    assert "Chicken" in recipe.tags


@pytest.mark.anyio
async def test_search_external_recipes_returns_mapped_results(monkeypatch):
    def handler(request):
        assert "search.php" in str(request.url)
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    results = await themealdb.search_external_recipes("chicken")
    assert len(results) == 1
    assert results[0].source == "external"


@pytest.mark.anyio
async def test_search_external_recipes_handles_no_matches(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"meals": None})

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    results = await themealdb.search_external_recipes("zzzznonexistent")
    assert results == []


@pytest.mark.anyio
async def test_search_external_recipes_skips_malformed_entries(monkeypatch):
    malformed_meal = {"idMeal": "1"}  # missing strMeal etc.

    def handler(request):
        return httpx.Response(200, json={"meals": [malformed_meal, SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    results = await themealdb.search_external_recipes("chicken")
    assert len(results) == 1
    assert results[0].id == "52772"


@pytest.mark.anyio
async def test_get_external_recipe_found(monkeypatch):
    def handler(request):
        assert "lookup.php" in str(request.url)
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    recipe = await themealdb.get_external_recipe("52772")
    assert recipe is not None
    assert recipe.id == "52772"


@pytest.mark.anyio
async def test_get_external_recipe_not_found(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"meals": None})

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    recipe = await themealdb.get_external_recipe("does-not-exist")
    assert recipe is None


@pytest.mark.anyio
async def test_get_raises_mealdb_error_on_timeout(monkeypatch):
    def handler(request):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    with pytest.raises(themealdb.MealDBError):
        await themealdb.search_external_recipes("chicken")


@pytest.mark.anyio
async def test_get_raises_mealdb_error_on_http_status_error(monkeypatch):
    def handler(request):
        return httpx.Response(500, text="server error")

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    with pytest.raises(themealdb.MealDBError):
        await themealdb.search_external_recipes("chicken")


@pytest.mark.anyio
async def test_search_external_recipes_empty_query_skips_call(monkeypatch):
    def handler(request):
        raise AssertionError("should not make a request for an empty query")

    monkeypatch.setattr(themealdb, "_build_client", _client_for(handler))

    results = await themealdb.search_external_recipes("   ")
    assert results == []
