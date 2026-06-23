"""
Test fixtures for Recipe Explorer tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_external_client, get_store, get_store_v2, get_user_store
from app.exceptions import ExternalAPIError
from app.main import app
from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.models_v2 import RecipeCreateV2, RecipeUpdateV2, RecipeV2, SortOrder
from app.services.fake_user_storage import FakeUserStorage
from app.services.metrics import metrics
from app.services.storage import RecipeStorage


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
    """Inject a fresh in-memory store for each test via DI override.

    This keeps tests isolated from the production SQLite database and from
    each other, while proving the DI layer works: the endpoints don't care
    whether they receive an in-memory store or a SQLite-backed one.
    """
    store = RecipeStorage()
    app.dependency_overrides[get_store] = lambda: store
    yield
    app.dependency_overrides.pop(get_store, None)


@pytest.fixture
def clean_metrics():
    """Reset timing metrics before and after each test."""
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture
def clean_user_storage():
    """Inject a fresh in-memory user store for each test via DI override."""
    store = FakeUserStorage()
    app.dependency_overrides[get_user_store] = lambda: store
    yield store
    app.dependency_overrides.pop(get_user_store, None)


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


# ---------------------------------------------------------------------------
# v2 test fixtures
# ---------------------------------------------------------------------------

_V2_EXTRA_FIELDS = set(RecipeV2.model_fields) - set(Recipe.model_fields)
_V1_FIELDS = set(Recipe.model_fields)


class FakeRecipeStoreV2:
    """In-memory store that implements both RecipeStore and RecipeStoreV2 protocols."""

    def __init__(self):
        self._recipes: Dict[str, RecipeV2] = {}

    # --- RecipeStore (v1 compat) ---

    def _to_v1(self, r: RecipeV2) -> Recipe:
        return Recipe.model_validate(r.model_dump(include=_V1_FIELDS))

    def get_all_recipes(self) -> List[Recipe]:
        return [self._to_v1(r) for r in self._recipes.values()]

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        r = self._recipes.get(recipe_id)
        return self._to_v1(r) if r else None

    def search_recipes(self, query: str) -> List[Recipe]:
        q = query.lower()
        return [self._to_v1(r) for r in self._recipes.values() if q in r.title.lower()]

    def create_recipe(self, data: RecipeCreate) -> Recipe:
        r = RecipeV2(**data.model_dump())
        self._recipes[r.id] = r
        return self._to_v1(r)

    def update_recipe(self, recipe_id: str, data: RecipeUpdate) -> Optional[Recipe]:
        if recipe_id not in self._recipes:
            return None
        existing = self._recipes[recipe_id]
        v2_extras = {k: getattr(existing, k) for k in _V2_EXTRA_FIELDS}
        updated = RecipeV2(**data.model_dump(), **v2_extras, id=recipe_id,
                           source=existing.source, created_at=existing.created_at,
                           updated_at=datetime.now())
        self._recipes[recipe_id] = updated
        return self._to_v1(updated)

    def delete_recipe(self, recipe_id: str) -> bool:
        if recipe_id in self._recipes:
            del self._recipes[recipe_id]
            return True
        return False

    def import_recipes(self, recipes_data: List[dict]) -> dict:
        self._recipes.clear()
        imported, errors = 0, []
        for i, rd in enumerate(recipes_data):
            try:
                r = RecipeV2(**rd)
                self._recipes[r.id] = r
                imported += 1
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        return {"imported": imported, "skipped": len(errors), "errors": errors}

    # --- RecipeStoreV2 ---

    def get_all_recipes_v2(self) -> List[RecipeV2]:
        return list(self._recipes.values())

    def get_recipe_v2(self, recipe_id: str) -> Optional[RecipeV2]:
        return self._recipes.get(recipe_id)

    def search_recipes_v2(
        self,
        query=None,
        cuisine=None,
        difficulty=None,
        dietary=None,
        sort=SortOrder.created_desc,
    ) -> List[RecipeV2]:
        results = list(self._recipes.values())
        if query:
            q = query.lower()
            results = [r for r in results if q in r.title.lower()
                       or q in r.description.lower()
                       or any(q in t.lower() for t in r.tags)]
        if cuisine:
            results = [r for r in results if r.cuisine.lower() == cuisine.lower()]
        if difficulty:
            results = [r for r in results if r.difficulty and r.difficulty.value == difficulty]
        if dietary:
            results = [r for r in results if any(d.value == dietary for d in r.dietary_restrictions)]
        reverse = sort.value.endswith("_desc")
        if "title" in sort.value:
            results.sort(key=lambda r: r.title.lower(), reverse=reverse)
        else:
            results.sort(key=lambda r: str(r.created_at), reverse=reverse)
        return results

    def get_recipes_by_ids(self, ids: List[str]) -> List[RecipeV2]:
        return [self._recipes[i] for i in ids if i in self._recipes]

    def create_recipe_v2(self, data: RecipeCreateV2) -> RecipeV2:
        r = RecipeV2(**data.model_dump())
        self._recipes[r.id] = r
        return r

    def update_recipe_v2(self, recipe_id: str, data: RecipeUpdateV2) -> Optional[RecipeV2]:
        if recipe_id not in self._recipes:
            return None
        existing = self._recipes[recipe_id]
        updated = RecipeV2(**data.model_dump(), id=recipe_id,
                           source=existing.source, created_at=existing.created_at,
                           updated_at=datetime.now())
        self._recipes[recipe_id] = updated
        return updated

    def bulk_create_v2(self, recipes: List[RecipeCreateV2]) -> tuple[List[RecipeV2], List[dict]]:
        created, errors = [], []
        for i, data in enumerate(recipes):
            try:
                created.append(self.create_recipe_v2(data))
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        return created, errors


@pytest.fixture
def clean_storage_v2():
    """Inject a fresh in-memory v2 store for each test."""
    store = FakeRecipeStoreV2()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_store_v2] = lambda: store
    yield store
    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(get_store_v2, None)


@pytest.fixture
def sample_recipe_data_v2():
    """Sample recipe with v2 fields for testing."""
    return {
        "title": "Vegan Pasta",
        "description": "A delicious plant-based pasta dish",
        "cuisine": "Italian",
        "ingredients": ["pasta", "tomatoes", "basil", "olive oil"],
        "instructions": ["Boil pasta.", "Make sauce.", "Combine and serve."],
        "tags": ["vegan", "pasta", "italian"],
        "difficulty": "beginner",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "servings": 4,
        "dietary_restrictions": ["vegan", "dairy_free"],
        "equipment": ["pot", "pan"],
        "techniques": ["boiling", "sautéing"],
        "nutritional_info": {"calories": 380, "protein_g": 12, "carbs_g": 68, "fat_g": 8, "fiber_g": 4},
        "related_recipe_ids": [],
    }
