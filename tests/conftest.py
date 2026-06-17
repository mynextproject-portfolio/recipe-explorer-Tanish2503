"""
Test fixtures for Recipe Explorer tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_external_client
from app.exceptions import ExternalAPIError
from app.main import app
from app.services.metrics import metrics
from app.services.storage import recipe_storage


class NullExternalClient:
    """Never hits the network. Default external client for all tests."""

    async def search(self, query: str) -> list:
        return []

    async def get_by_id(self, meal_id: str):
        return None


class FakeExternalClient:
    """Configurable fake external client for tests that need specific behaviour."""

    def __init__(
        self,
        *,
        search_results=(),
        lookup_result=None,
        search_raises: ExternalAPIError | None = None,
        lookup_raises: ExternalAPIError | None = None,
    ):
        self.search_results = list(search_results)
        self.lookup_result = lookup_result
        self.search_raises = search_raises
        self.lookup_raises = lookup_raises
        self.last_search_query: str | None = None

    async def search(self, query: str):
        self.last_search_query = query
        if self.search_raises:
            raise self.search_raises
        return self.search_results

    async def get_by_id(self, meal_id: str):
        if self.lookup_raises:
            raise self.lookup_raises
        return self.lookup_result


@pytest.fixture(autouse=True)
def _default_null_external():
    """Prevent every test from hitting the real external API.

    Tests that need specific external behaviour set app.dependency_overrides
    inside their body; this fixture cleans up the key afterwards.
    """
    app.dependency_overrides[get_external_client] = lambda: NullExternalClient()
    yield
    app.dependency_overrides.pop(get_external_client, None)


@pytest.fixture
def client():
    """Test client for making requests to the API."""
    return TestClient(app)


@pytest.fixture
def clean_storage():
    """Reset storage before and after each test."""
    recipe_storage.recipes.clear()
    yield
    recipe_storage.recipes.clear()


@pytest.fixture
def clean_metrics():
    """Reset timing metrics before and after each test."""
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture
def sample_recipe_data():
    """Sample recipe for testing."""
    return {
        "title": "Test Recipe",
        "description": "A test recipe",
        "cuisine": "American",
        "ingredients": ["ingredient 1", "ingredient 2"],
        "instructions": ["First, do step 1.", "Then, do step 2."],
        "tags": ["test"],
    }
