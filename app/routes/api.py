import json
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.dependencies import (
    ExternalRecipeClient,
    RecipeStore,
    get_external_client,
    get_store,
)
from app.exceptions import ExternalAPIError
from app.models import RecipeCreate, RecipeUpdate
from app.services.metrics import metrics, timed

router = APIRouter(prefix="/api")

MAX_IMPORT_FILE_SIZE = 1_000_000  # 1MB


async def _combined_search(
    term: Optional[str],
    store: RecipeStore,
    external: ExternalRecipeClient,
) -> dict:
    """Search internal storage and, if a term is given, the external client too."""
    if not term:
        with timed("internal", "list_all") as timer:
            recipes = store.get_all_recipes()
        return {
            "recipes": recipes,
            "timing": {"internal_ms": round(timer.duration_ms, 2)},
        }

    with timed("internal", "search") as internal_timer:
        recipes = store.search_recipes(term)
    timing = {"internal_ms": round(internal_timer.duration_ms, 2)}

    try:
        with timed("external", "search") as external_timer:
            external_recipes = await external.search(term)
        timing["external_ms"] = round(external_timer.duration_ms, 2)
    except ExternalAPIError as error:
        return {
            "recipes": recipes,
            "external_search_error": str(error),
            "timing": timing,
        }

    return {"recipes": recipes + external_recipes, "timing": timing}


@router.get("/recipes")
async def get_recipes(
    search: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Get all recipes, or search internal recipes plus the external source by title."""
    return await _combined_search(search, store, external)


@router.get("/recipes/search")
async def search_recipes_endpoint(
    q: Optional[str] = None,
    search: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Search internal recipes plus external source by title (q or search param)."""
    return await _combined_search(q or search, store, external)


@router.get("/recipes/export")
def export_recipes(store: RecipeStore = Depends(get_store)):
    """Export all recipes as JSON."""
    recipes = store.get_all_recipes()
    return JSONResponse(content=jsonable_encoder([r.model_dump() for r in recipes]))


@router.get("/recipes/external/{meal_id}")
async def get_external_recipe(
    meal_id: str,
    response: Response,
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Get a specific recipe by ID from the external source."""
    try:
        with timed("external", "lookup") as timer:
            recipe = await external.get_by_id(meal_id)
    except ExternalAPIError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
            headers={"X-Query-Time-Ms": f"{timer.duration_ms:.2f}"},
        )

    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(
            status_code=404, detail=f"External recipe '{meal_id}' not found"
        )
    return recipe


@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: str,
    response: Response,
    store: RecipeStore = Depends(get_store),
):
    """Get a specific recipe by ID."""
    with timed("internal", "lookup") as timer:
        recipe = store.get_recipe(recipe_id)
    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return recipe


@router.get("/metrics")
def get_metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/metrics/summary")
def get_metrics_summary():
    """View aggregated timing metrics for internal storage vs external API calls."""
    return {"metrics": metrics.summary()}


@router.post("/recipes")
def create_recipe(recipe: RecipeCreate, store: RecipeStore = Depends(get_store)):
    """Create a new recipe."""
    return store.create_recipe(recipe)


@router.put("/recipes/{recipe_id}")
def update_recipe(
    recipe_id: str,
    recipe: RecipeUpdate,
    store: RecipeStore = Depends(get_store),
):
    """Update an existing recipe."""
    updated = store.update_recipe(recipe_id, recipe)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return updated


@router.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: str, store: RecipeStore = Depends(get_store)):
    """Delete a recipe."""
    if not store.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return {"message": "Recipe deleted successfully", "status": "success"}


@router.post("/recipes/import")
async def import_recipes(
    file: UploadFile = File(...),
    store: RecipeStore = Depends(get_store),
):
    """Import recipes from a JSON file, replacing all existing recipes."""
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are supported")

    content = await file.read()
    if len(content) > MAX_IMPORT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")

    try:
        recipes_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e.msg}")

    if not isinstance(recipes_data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of recipes")

    result = store.import_recipes(recipes_data)
    return {
        "message": f"Imported {result['imported']} of {len(recipes_data)} recipes",
        "imported": result["imported"],
        "skipped": result["skipped"],
        "errors": result["errors"],
    }
