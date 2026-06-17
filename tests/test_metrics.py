"""
Contract tests for the timing instrumentation: response timing data,
X-Query-Time-Ms headers, and the /api/metrics aggregation endpoint.
"""

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


def test_list_all_includes_internal_timing_only(client, clean_storage, clean_metrics):
    response = client.get("/api/recipes")
    assert response.status_code == 200

    timing = response.json()["timing"]
    assert "internal_ms" in timing
    assert "external_ms" not in timing


def test_search_includes_both_timings(
    client, clean_storage, clean_metrics, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    assert response.status_code == 200

    timing = response.json()["timing"]
    assert "internal_ms" in timing
    assert "external_ms" in timing
    assert isinstance(timing["internal_ms"], float)
    assert isinstance(timing["external_ms"], float)


def test_search_failure_still_reports_internal_timing(
    client, clean_storage, clean_metrics, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_raises=ExternalAPIError("TheMealDB API timed out")
    )

    response = client.get("/api/recipes", params={"search": "Test"})
    body = response.json()
    assert "internal_ms" in body["timing"]
    assert "external_ms" not in body["timing"]


def test_internal_lookup_sets_response_header(
    client, clean_storage, clean_metrics, sample_recipe_data
):
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    response = client.get(f"/api/recipes/{recipe_id}")
    assert response.status_code == 200
    assert "X-Query-Time-Ms" in response.headers


def test_external_lookup_sets_response_header(client, clean_metrics):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        lookup_result=EXTERNAL_RECIPE
    )

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 200
    assert "X-Query-Time-Ms" in response.headers


def test_external_lookup_failure_still_sets_header(client, clean_metrics):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        lookup_raises=ExternalAPIError("TheMealDB API is unreachable")
    )

    response = client.get("/api/recipes/external/52772")
    assert response.status_code == 502
    assert "X-Query-Time-Ms" in response.headers


def test_metrics_endpoint_aggregates_internal_and_external(
    client, clean_storage, clean_metrics, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    client.get("/api/recipes", params={"search": "Test"})
    client.get("/api/recipes", params={"search": "Test"})

    response = client.get("/api/metrics/summary")
    assert response.status_code == 200

    body = response.json()["metrics"]
    assert body["internal"]["search"]["count"] == 2
    assert body["external"]["search"]["count"] == 2
    for source in ("internal", "external"):
        for field in ("avg_ms", "min_ms", "max_ms"):
            assert field in body[source]["search"]


def test_metrics_start_empty(client, clean_metrics):
    response = client.get("/api/metrics/summary")
    assert response.status_code == 200
    assert response.json()["metrics"] == {}


def test_home_page_shows_timing_info(
    client, clean_storage, clean_metrics, sample_recipe_data
):
    client.post("/api/recipes", json=sample_recipe_data)
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        search_results=[EXTERNAL_RECIPE]
    )

    response = client.get("/", params={"search": "Test"})
    assert response.status_code == 200
    assert "Query time" in response.text
    assert "external (TheMealDB)" in response.text
