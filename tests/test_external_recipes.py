"""
Contract tests for the external recipe integration exposed through the API and
HTML pages. Dependencies are swapped via FastAPI's dependency_overrides so
these tests never hit the real network.
"""

import pytest
from tests.conftest import FakeExternalClient

from app.dependencies import get_external_client
from app.exceptions import ExternalAPIError
from app.main import app
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


# ---------------------------------------------------------------------------
# API: /api/recipes (search)
# ---------------------------------------------------------------------------


def test_search_combines_internal_and_external_results(
    client, clean_storage, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200

    sources = {r["source"] for r in response.json()["recipes"]}
    assert sources == {"internal", "external"}


def test_search_without_query_skips_external_call(client, clean_storage):
    class _AssertNotCalled:
        async def search(self, query):
            raise AssertionError("external search must not be called without a term")

        async def get_by_id(self, meal_id):
            return None

    app.dependency_overrides[get_external_client] = lambda: _AssertNotCalled()

    response = client.get("/api/recipes")
    assert response.status_code == 200


def test_search_degrades_gracefully_when_external_api_fails(
    client, clean_storage, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_raises=ExternalAPIError("TheMealDB API timed out")
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200

    body = response.json()
    assert len(body["recipes"]) == 1
    assert body["recipes"][0]["source"] == "internal"
    assert "external_search_error" in body


# ---------------------------------------------------------------------------
# API: /api/recipes/external/{meal_id}
# ---------------------------------------------------------------------------


def test_get_external_recipe_success(client):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        lookup_result=EXTERNAL_RECIPE
    )

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 200
    assert response.json()["source"] == "external"
    assert response.json()["id"] == "52772"


def test_get_external_recipe_not_found(client):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        lookup_result=None
    )

    response = client.get("/api/recipes/external/does-not-exist")
    assert response.status_code == 404


def test_get_external_recipe_upstream_failure_returns_502(client):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        lookup_raises=ExternalAPIError("TheMealDB API is unreachable")
    )

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# API: /api/recipes/search (alias endpoint)
# ---------------------------------------------------------------------------


def test_search_endpoint_alias_combines_both_sources(
    client, clean_storage, sample_recipe_data
):
    """GET /api/recipes/search?q= must not be swallowed by the {recipe_id} route."""
    client.post("/api/recipes", json=sample_recipe_data)
    fake = FakeExternalClient(search_results=[EXTERNAL_RECIPE])
    app.dependency_overrides[get_external_client] = lambda: fake

    response = client.get("/api/recipes/search", params={"q": "arrabiata"})
    assert response.status_code == 200
    assert fake.last_search_query == "arrabiata"

    sources = {r["source"] for r in response.json()["recipes"]}
    assert "external" in sources


def test_search_endpoint_alias_accepts_search_param(client, clean_storage):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    response = client.get("/api/recipes/search", params={"search": "arrabiata"})
    assert response.status_code == 200
    assert len(response.json()["recipes"]) == 1


# ---------------------------------------------------------------------------
# API: SPA routes serve index.html (React handles rendering)
# ---------------------------------------------------------------------------


def test_spa_root_returns_html(client):
    """The root route serves the React SPA index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_spa_recipe_route_returns_html(client):
    """Client-side routes serve the React SPA (React Router handles them)."""
    response = client.get("/recipes/external/52772")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_search_combines_internal_and_external(
    client, clean_storage, sample_recipe_data
):
    """API search merges internal + external results (used by React frontend)."""
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200
    body = response.json()
    titles = [r["title"] for r in body["recipes"]]
    assert EXTERNAL_RECIPE.title in titles
    external_sources = [r["source"] for r in body["recipes"] if r["source"] == "external"]
    assert external_sources


def test_api_search_degrades_gracefully_on_external_failure(
    client, clean_storage, sample_recipe_data
):
    """API returns error field when external API fails (React shows it)."""
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_raises=ExternalAPIError("TheMealDB API timed out")
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200
    body = response.json()
    assert "external_search_error" in body
    assert "TheMealDB API timed out" in body["external_search_error"]
