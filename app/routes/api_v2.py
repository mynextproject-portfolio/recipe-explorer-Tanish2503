"""
/api/v2/recipes — enhanced recipe API.

New in v2:
  - Extended schema: difficulty, prep/cook time, servings, nutritional info,
    dietary restrictions, equipment, techniques, related recipe IDs.
  - Richer search: filter by cuisine, difficulty, dietary restriction; sort by
    any scalar field.
  - Bulk GET via ?ids= query parameter.
  - Bulk create via POST /api/v2/recipes/bulk.
  - External recipe lookup at /api/v2/recipes/external/{id}.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.dependencies import (
    ExternalRecipeClient,
    RecipeStoreV2,
    get_external_client,
    get_store_v2,
)
from app.exceptions import ExternalAPIError
from app.models_v2 import (
    BulkCreateRequest,
    BulkCreateResponse,
    RecipeCreateV2,
    RecipeUpdateV2,
    RecipeV2,
    SortOrder,
)
from app.routes.api import _combined_search
from app.services.metrics import timed

router = APIRouter(prefix="/api/v2")


@router.get("/recipes", response_model=None)
async def get_recipes_v2(
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    difficulty: Optional[str] = None,
    dietary: Optional[str] = None,
    sort: SortOrder = SortOrder.created_desc,
    ids: Optional[str] = None,
    store: RecipeStoreV2 = Depends(get_store_v2),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """List recipes with v2 schema. Supports filtering, sorting, and bulk ID fetch.

    - `ids`: comma-separated list of recipe IDs — returns exactly those records
    - `search`: text match against title, description, and tags
    - `cuisine`: exact cuisine filter (case-insensitive)
    - `difficulty`: one of beginner | intermediate | advanced | expert
    - `dietary`: one of vegetarian | vegan | gluten_free | dairy_free | nut_free | halal | kosher | low_carb
    - `sort`: created_asc | created_desc | title_asc | title_desc | difficulty_asc | difficulty_desc
    """
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        recipes = store.get_recipes_by_ids(id_list)
        return {"recipes": recipes}

    if search or cuisine or difficulty or dietary or sort != SortOrder.created_desc:
        internal = store.search_recipes_v2(
            query=search,
            cuisine=cuisine,
            difficulty=difficulty,
            dietary=dietary,
            sort=sort,
        )
        if search:
            try:
                external_recipes = await external.search(search)
            except ExternalAPIError:
                external_recipes = []
            # External recipes are v1 Recipe objects; they don't have v2 fields.
            # Wrap them as RecipeV2 with defaults so the response schema is consistent.
            external_v2 = [
                RecipeV2(**r.model_dump()) for r in external_recipes
            ]
            return {"recipes": internal + external_v2}
        return {"recipes": internal}

    # No filters — return all internal recipes (v2) + external if searching
    recipes = store.get_all_recipes_v2()
    return {"recipes": recipes}


@router.get("/recipes/export")
def export_recipes_v2(store: RecipeStoreV2 = Depends(get_store_v2)):
    """Export all internal recipes as JSON with full v2 schema."""
    recipes = store.get_all_recipes_v2()
    return JSONResponse(content=jsonable_encoder([r.model_dump() for r in recipes]))


@router.get("/recipes/external/{meal_id}")
async def get_external_recipe_v2(
    meal_id: str,
    response: Response,
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Fetch an external recipe by TheMealDB ID. Wrapped in v2 schema with null v2 fields."""
    try:
        with timed("external", "lookup") as timer:
            recipe = await external.get_by_id(meal_id)
    except ExternalAPIError as error:
        raise HTTPException(status_code=502, detail=str(error))

    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"External recipe '{meal_id}' not found")
    return RecipeV2(**recipe.model_dump())


@router.get("/recipes/{recipe_id}")
def get_recipe_v2(
    recipe_id: str,
    response: Response,
    store: RecipeStoreV2 = Depends(get_store_v2),
):
    """Get a single recipe with full v2 schema."""
    with timed("internal", "lookup") as timer:
        recipe = store.get_recipe_v2(recipe_id)
    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return recipe


@router.post("/recipes", status_code=201)
def create_recipe_v2(
    recipe: RecipeCreateV2,
    store: RecipeStoreV2 = Depends(get_store_v2),
) -> RecipeV2:
    """Create a recipe with full v2 fields. Returns 201 Created."""
    return store.create_recipe_v2(recipe)


@router.post("/recipes/bulk", status_code=201)
def bulk_create_recipes_v2(
    body: BulkCreateRequest,
    store: RecipeStoreV2 = Depends(get_store_v2),
) -> BulkCreateResponse:
    """Create up to 50 recipes in one request.

    Each recipe is validated and inserted independently — one failure does not
    abort the rest. The response contains both the successful creations and an
    error list for failed entries.
    """
    created, errors = store.bulk_create_v2(body.recipes)
    return BulkCreateResponse(
        created=created,
        errors=errors,
        total_requested=len(body.recipes),
    )


@router.put("/recipes/{recipe_id}")
def update_recipe_v2(
    recipe_id: str,
    recipe: RecipeUpdateV2,
    store: RecipeStoreV2 = Depends(get_store_v2),
) -> RecipeV2:
    """Update an existing recipe. Accepts full v2 schema."""
    updated = store.update_recipe_v2(recipe_id, recipe)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return updated


@router.delete("/recipes/{recipe_id}", status_code=200)
def delete_recipe_v2(recipe_id: str, store: RecipeStoreV2 = Depends(get_store_v2)):
    """Delete a recipe by ID."""
    # Delegate to the parent store's delete (v1 and v2 share the same table row)
    if not store.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return {"message": "Recipe deleted successfully", "status": "success"}
