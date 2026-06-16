from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
import json
from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.services.storage import recipe_storage

router = APIRouter(prefix="/api")

MAX_IMPORT_FILE_SIZE = 1_000_000  # 1MB


@router.get("/recipes")
def get_recipes(search: Optional[str] = None):
    """Get all recipes or search by title"""
    # TODO: Add pagination when we have more than 100 recipes
    if search:
        recipes = recipe_storage.search_recipes(search)
    else:
        recipes = recipe_storage.get_all_recipes()

    return {"recipes": recipes}


@router.get("/recipes/export")
def export_recipes():
    """Export all recipes as JSON"""
    recipes = recipe_storage.get_all_recipes()
    # Convert to dict for JSON serialization; jsonable_encoder handles datetimes
    recipes_dict = [recipe.model_dump() for recipe in recipes]
    return JSONResponse(content=jsonable_encoder(recipes_dict))


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str):
    """Get a specific recipe by ID"""
    recipe = recipe_storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return recipe


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
