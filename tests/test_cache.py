"""
Tests for Redis caching in the TheMealDB adapter.

All tests use an in-memory FakeCache so they never touch Redis, and a mock
HTTP transport so they never hit the real network.
"""

import httpx
import pytest

from app.services import themealdb
from app.services.cache import RecipeCache
from app.services.metrics import metrics

SAMPLE_MEAL = {
    "idMeal": "52772",
    "strMeal": "Teriyaki Chicken Casserole",
    "strCategory": "Chicken",
    "strArea": "Japanese",
    "strInstructions": "Preheat oven to 350F.\r\nBake for 30 minutes.",
    "strTags": "Meat",
    "strIngredient1": "soy sauce",
    "strMeasure1": "3/4 cup",
    "strIngredient2": "",
    "strMeasure2": "",
}


class FakeCache:
    """In-memory cache substitute for unit tests."""

    def __init__(self, initial: dict | None = None):
        self._store: dict = initial or {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple] = []

    @property
    def available(self) -> bool:
        return True

    async def get(self, key: str):
        self.get_calls.append(key)
        return self._store.get(key)

    async def set(self, key: str, value, ttl: int = 86400) -> None:
        self.set_calls.append((key, value, ttl))
        self._store[key] = value


class NullCache:
    """Cache that always reports a miss and never stores anything."""

    @property
    def available(self) -> bool:
        return False

    async def get(self, key: str):
        return None

    async def set(self, key: str, value, ttl: int = 86400) -> None:
        pass


def _mock_client(handler):
    def factory():
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=themealdb.MEALDB_BASE_URL,
            timeout=themealdb.REQUEST_TIMEOUT,
        )

    return factory


# ---------------------------------------------------------------------------
# RecipeCache unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_recipe_cache_get_returns_none_when_disconnected():
    cache = RecipeCache()
    assert await cache.get("any-key") is None


@pytest.mark.anyio
async def test_recipe_cache_set_is_noop_when_disconnected():
    cache = RecipeCache()
    await cache.set("key", {"some": "data"})  # should not raise


@pytest.mark.anyio
async def test_recipe_cache_available_is_false_when_disconnected():
    cache = RecipeCache()
    assert cache.available is False


# ---------------------------------------------------------------------------
# Cache hit / miss in search_external_recipes
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_returns_cached_results_without_hitting_api(
    monkeypatch, clean_metrics
):
    from app.models import Recipe

    cached_recipe = Recipe(
        id="52772",
        title="Teriyaki Chicken Casserole",
        description="Chicken dish from Japanese",
        cuisine="Japanese",
        ingredients=["3/4 cup soy sauce"],
        instructions=["Preheat oven.", "Bake."],
        tags=["Meat"],
        source="external",
    )
    cached_data = [cached_recipe.model_dump(mode="json")]
    fake_cache = FakeCache({"mealdb:search:chicken": cached_data})

    def should_not_be_called():
        raise AssertionError("API must not be called on cache hit")

    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)
    monkeypatch.setattr(themealdb, "_build_client", should_not_be_called)

    results = await themealdb.search_external_recipes("chicken")

    assert len(results) == 1
    assert results[0].id == "52772"
    assert results[0].source == "external"


@pytest.mark.anyio
async def test_search_cache_hit_records_metric(monkeypatch, clean_metrics):
    from app.models import Recipe

    cached_recipe = Recipe(
        id="52772",
        title="Teriyaki Chicken Casserole",
        description="Chicken dish from Japanese",
        cuisine="Japanese",
        ingredients=["3/4 cup soy sauce"],
        instructions=["Preheat oven.", "Bake."],
        tags=["Meat"],
        source="external",
    )
    fake_cache = FakeCache(
        {"mealdb:search:chicken": [cached_recipe.model_dump(mode="json")]}
    )
    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)

    await themealdb.search_external_recipes("chicken")

    summary = metrics.summary()
    assert summary["cache"]["search"]["hits"] == 1
    assert summary["cache"]["search"]["misses"] == 0


@pytest.mark.anyio
async def test_search_cache_miss_calls_api_and_populates_cache(
    monkeypatch, clean_metrics
):
    fake_cache = FakeCache()

    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    results = await themealdb.search_external_recipes("chicken")

    assert len(results) == 1
    assert results[0].id == "52772"
    # Cache must have been populated
    assert len(fake_cache.set_calls) == 1
    key, value, ttl = fake_cache.set_calls[0]
    assert key == "mealdb:search:chicken"
    assert ttl == 86400


@pytest.mark.anyio
async def test_search_cache_miss_records_metric(monkeypatch, clean_metrics):
    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", FakeCache())
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    await themealdb.search_external_recipes("chicken")

    summary = metrics.summary()
    assert summary["cache"]["search"]["misses"] == 1
    assert summary["cache"]["search"]["hits"] == 0


@pytest.mark.anyio
async def test_search_uses_normalized_cache_key(monkeypatch, clean_metrics):
    """Searches differing only by case must share the same cache entry."""
    fake_cache = FakeCache()

    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    await themealdb.search_external_recipes("Chicken")
    await themealdb.search_external_recipes("chicken")

    # First call: miss → set. Second call: hit → no additional set.
    assert len(fake_cache.set_calls) == 1


# ---------------------------------------------------------------------------
# Cache hit / miss in get_external_recipe
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_lookup_returns_cached_recipe_without_hitting_api(
    monkeypatch, clean_metrics
):
    from app.models import Recipe

    cached_recipe = Recipe(
        id="52772",
        title="Teriyaki Chicken Casserole",
        description="Chicken dish from Japanese",
        cuisine="Japanese",
        ingredients=["3/4 cup soy sauce"],
        instructions=["Preheat oven.", "Bake."],
        tags=["Meat"],
        source="external",
    )
    fake_cache = FakeCache(
        {"mealdb:lookup:52772": cached_recipe.model_dump(mode="json")}
    )

    def should_not_be_called():
        raise AssertionError("API must not be called on cache hit")

    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)
    monkeypatch.setattr(themealdb, "_build_client", should_not_be_called)

    result = await themealdb.get_external_recipe("52772")

    assert result is not None
    assert result.id == "52772"


@pytest.mark.anyio
async def test_lookup_cache_hit_records_metric(monkeypatch, clean_metrics):
    from app.models import Recipe

    cached_recipe = Recipe(
        id="52772",
        title="Teriyaki Chicken Casserole",
        description="Chicken dish from Japanese",
        cuisine="Japanese",
        ingredients=["3/4 cup soy sauce"],
        instructions=["Preheat oven.", "Bake."],
        tags=["Meat"],
        source="external",
    )
    fake_cache = FakeCache(
        {"mealdb:lookup:52772": cached_recipe.model_dump(mode="json")}
    )
    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)

    await themealdb.get_external_recipe("52772")

    summary = metrics.summary()
    assert summary["cache"]["lookup"]["hits"] == 1


@pytest.mark.anyio
async def test_lookup_cache_miss_populates_cache(monkeypatch, clean_metrics):
    fake_cache = FakeCache()

    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", fake_cache)
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    result = await themealdb.get_external_recipe("52772")

    assert result is not None
    assert len(fake_cache.set_calls) == 1
    key, value, ttl = fake_cache.set_calls[0]
    assert key == "mealdb:lookup:52772"
    assert ttl == 86400


# ---------------------------------------------------------------------------
# Graceful degradation when Redis is unavailable
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_works_when_cache_unavailable(monkeypatch, clean_metrics):
    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", NullCache())
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    results = await themealdb.search_external_recipes("chicken")

    assert len(results) == 1
    assert results[0].id == "52772"


@pytest.mark.anyio
async def test_lookup_works_when_cache_unavailable(monkeypatch, clean_metrics):
    def handler(request):
        return httpx.Response(200, json={"meals": [SAMPLE_MEAL]})

    monkeypatch.setattr(themealdb, "recipe_cache", NullCache())
    monkeypatch.setattr(themealdb, "_build_client", _mock_client(handler))

    result = await themealdb.get_external_recipe("52772")

    assert result is not None
    assert result.id == "52772"


# ---------------------------------------------------------------------------
# Metrics summary includes cache stats
# ---------------------------------------------------------------------------


def test_metrics_summary_includes_cache_section(clean_metrics):
    metrics.record_cache_result("search", hit=True)
    metrics.record_cache_result("search", hit=True)
    metrics.record_cache_result("search", hit=False)

    summary = metrics.summary()
    assert "cache" in summary
    assert summary["cache"]["search"]["hits"] == 2
    assert summary["cache"]["search"]["misses"] == 1
    assert summary["cache"]["search"]["hit_rate"] == pytest.approx(2 / 3, rel=1e-3)


def test_metrics_reset_clears_cache_counters(clean_metrics):
    metrics.record_cache_result("search", hit=True)
    metrics.reset()

    summary = metrics.summary()
    assert "cache" not in summary
