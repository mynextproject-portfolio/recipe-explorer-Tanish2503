"""
Dependency injection contracts and provider functions.

Protocols define the shape expected by routes; provider functions return the
default singleton implementations. Tests override providers via
``app.dependency_overrides[get_store] = lambda: FakeStore()``.
"""

from typing import List, Optional, Protocol

from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.services.metrics import TimingMetrics
from app.services.metrics import metrics as _metrics_instance
from app.services.storage import recipe_storage
from app.services.themealdb import MealDBClient


class RecipeStore(Protocol):
    def get_all_recipes(self) -> List[Recipe]: ...

    def search_recipes(self, query: str) -> List[Recipe]: ...

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]: ...

    def create_recipe(self, data: RecipeCreate) -> Recipe: ...

    def update_recipe(
        self, recipe_id: str, data: RecipeUpdate
    ) -> Optional[Recipe]: ...

    def delete_recipe(self, recipe_id: str) -> bool: ...

    def import_recipes(self, recipes_data: List[dict]) -> dict: ...


class ExternalRecipeClient(Protocol):
    async def search(self, query: str) -> List[Recipe]: ...

    async def get_by_id(self, meal_id: str) -> Optional[Recipe]: ...


def get_store() -> RecipeStore:
    return recipe_storage


def get_external_client() -> ExternalRecipeClient:
    return MealDBClient()


def get_metrics() -> TimingMetrics:
    return _metrics_instance
