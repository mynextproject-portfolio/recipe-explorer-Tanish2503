from fastapi import APIRouter, HTTPException, Response, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional
import json
from app.models import RecipeCreate, RecipeUpdate
from app.services.storage import recipe_storage
from app.services import themealdb
from app.services.metrics import metrics, timed

router = APIRouter(prefix="/api")

MAX_IMPORT_FILE_SIZE = 1_000_000  # 1MB


async def _combined_search(term: Optional[str]) -> dict:
    """Search internal storage and, if a term is given, TheMealDB too."""
    if not term:
        with timed("internal", "list_all") as timer:
            recipes = recipe_storage.get_all_recipes()
        return {
            "recipes": recipes,
            "timing": {"internal_ms": round(timer.duration_ms, 2)},
        }

    with timed("internal", "search") as internal_timer:
        recipes = recipe_storage.search_recipes(term)
    timing = {"internal_ms": round(internal_timer.duration_ms, 2)}

    try:
        with timed("external", "search") as external_timer:
            external_recipes = await themealdb.search_external_recipes(term)
        timing["external_ms"] = round(external_timer.duration_ms, 2)
    except themealdb.MealDBError as error:
        return {
            "recipes": recipes,
            "external_search_error": str(error),
            "timing": timing,
        }

    return {"recipes": recipes + external_recipes, "timing": timing}


@router.get("/recipes")
async def get_recipes(search: Optional[str] = None):
    """Get all recipes, or search internal recipes plus TheMealDB by title"""
    # TODO: Add pagination when we have more than 100 recipes
    return await _combined_search(search)


@router.get("/recipes/search")
async def search_recipes_endpoint(
    q: Optional[str] = None, search: Optional[str] = None
):
    """Search internal recipes plus TheMealDB by title (q or search query param)"""
    return await _combined_search(q or search)


@router.get("/recipes/export")
def export_recipes():
    """Export all recipes as JSON"""
    recipes = recipe_storage.get_all_recipes()
    # Convert to dict for JSON serialization; jsonable_encoder handles datetimes
    recipes_dict = [recipe.model_dump() for recipe in recipes]
    return JSONResponse(content=jsonable_encoder(recipes_dict))


@router.get("/recipes/external/{meal_id}")
async def get_external_recipe(meal_id: str, response: Response):
    """Get a specific recipe by ID from TheMealDB"""
    try:
        with timed("external", "lookup") as timer:
            recipe = await themealdb.get_external_recipe(meal_id)
    except themealdb.MealDBError as error:
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
def get_recipe(recipe_id: str, response: Response):
    """Get a specific recipe by ID"""
    with timed("internal", "lookup") as timer:
        recipe = recipe_storage.get_recipe(recipe_id)
    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return recipe


@router.get("/metrics")
def get_metrics():
    """View aggregated timing metrics for internal storage vs external (TheMealDB) calls"""
    return {"metrics": metrics.summary()}


@router.post("/recipes")
def create_recipe(recipe: RecipeCreate):
    """Create a new recipe"""
    new_recipe = recipe_storage.create_recipe(recipe)
    return new_recipe


@router.put("/recipes/{recipe_id}")
def update_recipe(recipe_id: str, recipe: RecipeUpdate):
    """Update an existing recipe"""
    updated_recipe = recipe_storage.update_recipe(recipe_id, recipe)
    if not updated_recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return updated_recipe


@router.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: str):
    """Delete a recipe"""
    success = recipe_storage.delete_recipe(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return {"message": "Recipe deleted successfully", "status": "success"}


@router.post("/recipes/import")
async def import_recipes(file: UploadFile = File(...)):
    """Import recipes from a JSON file, replacing all existing recipes"""
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

    result = recipe_storage.import_recipes(recipes_data)
    return {
        "message": f"Imported {result['imported']} of {len(recipes_data)} recipes",
        "imported": result["imported"],
        "skipped": result["skipped"],
        "errors": result["errors"],
    }
