"""
Adapter for TheMealDB API (https://www.themealdb.com/api.php).

Fetches recipes in real time and transforms them into our internal Recipe
schema, tagged with source="external". Results are cached in Redis for 24h
so repeated searches don't hit the upstream API.
"""

from typing import List, Optional
import httpx

from app.models import Recipe
from app.services.cache import recipe_cache
from app.services.metrics import metrics

MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"
REQUEST_TIMEOUT = 5.0


class MealDBError(Exception):
    """Raised when TheMealDB can't be reached or returns something we can't use."""


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=MEALDB_BASE_URL, timeout=REQUEST_TIMEOUT)


async def _get(path: str, params: dict) -> dict:
    try:
        async with _build_client() as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as error:
        raise MealDBError("TheMealDB API timed out") from error
    except httpx.HTTPStatusError as error:
        raise MealDBError(
            f"TheMealDB API returned status {error.response.status_code}"
        ) from error
    except httpx.HTTPError as error:
        raise MealDBError("TheMealDB API is unreachable") from error
    except ValueError as error:
        raise MealDBError("TheMealDB API returned invalid JSON") from error


def _to_recipe(meal: dict) -> Recipe:
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if not name:
            continue
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        ingredients.append(f"{measure} {name}".strip() if measure else name)

    instructions_text = (meal.get("strInstructions") or "").replace("\r\n", "\n")
    instructions = [
        step.strip() for step in instructions_text.split("\n") if step.strip()
    ]

    tags = [
        tag.strip() for tag in (meal.get("strTags") or "").split(",") if tag.strip()
    ]
    category = (meal.get("strCategory") or "").strip()
    if category:
        tags.append(category)

    area = (meal.get("strArea") or "").strip()
    description = (
        f"{category} dish from {area}".strip()
        if category or area
        else "Recipe from TheMealDB"
    )

    return Recipe(
        id=meal["idMeal"],
        title=meal["strMeal"],
        description=description,
        cuisine=area,
        ingredients=ingredients,
        instructions=instructions,
        tags=tags,
        source="external",
    )


async def search_external_recipes(query: str) -> List[Recipe]:
    """Search TheMealDB by name, skipping any entries that don't fit our schema."""
    if not query or not query.strip():
        return []

    cache_key = f"mealdb:search:{query.lower().strip()}"
    cached = await recipe_cache.get(cache_key)
    if cached is not None:
        metrics.record_cache_result("search", hit=True)
        return [Recipe(**r) for r in cached]

    metrics.record_cache_result("search", hit=False)
    data = await _get("/search.php", {"s": query})
    meals = data.get("meals") or []

    recipes = []
    for meal in meals:
        try:
            recipes.append(_to_recipe(meal))
        except Exception:
            continue

    await recipe_cache.set(cache_key, [r.model_dump(mode="json") for r in recipes])
    return recipes


async def get_external_recipe(meal_id: str) -> Optional[Recipe]:
    """Look up a single TheMealDB recipe by its id."""
    cache_key = f"mealdb:lookup:{meal_id}"
    cached = await recipe_cache.get(cache_key)
    if cached is not None:
        metrics.record_cache_result("lookup", hit=True)
        return Recipe(**cached)

    metrics.record_cache_result("lookup", hit=False)
    data = await _get("/lookup.php", {"i": meal_id})
    meals = data.get("meals") or []
    if not meals:
        return None

    try:
        recipe = _to_recipe(meals[0])
    except Exception as error:
        raise MealDBError("TheMealDB returned malformed recipe data") from error

    await recipe_cache.set(cache_key, recipe.model_dump(mode="json"))
    return recipe
