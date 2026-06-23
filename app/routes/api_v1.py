"""
/api/v1/recipes — versioned aliases for the stable recipe API.

Every response carries RFC 8594 deprecation headers pointing clients to v2.
The business logic is identical to /api/recipes; only the URL prefix and
response headers differ.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.dependencies import ExternalRecipeClient, RecipeStore, get_external_client, get_store
from app.exceptions import ExternalAPIError
from app.models import RecipeCreate, RecipeUpdate
from app.routes.api import _combined_search
from app.services.metrics import timed

# RFC 8594 / sunset header values
_DEPRECATED_SINCE = "Mon, 23 Jun 2026 00:00:00 GMT"
_SUNSET_DATE = "Thu, 01 Jan 2027 00:00:00 GMT"
_LINK = '</api/v2/recipes>; rel="successor-version"'


class _DeprecatedRoute(APIRoute):
    """Injects Deprecation, Sunset, and Link headers on every v1 response."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def _handler(request: Request) -> Response:
            try:
                response = await original(request)
            except HTTPException as exc:
                # Convert to a plain JSONResponse so we can attach headers.
                # HTTPException responses bypass the normal route-handler path,
                # so we must intercept them here.
                response = JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers=dict(exc.headers or {}),
                )
            response.headers["Deprecation"] = _DEPRECATED_SINCE
            response.headers["Sunset"] = _SUNSET_DATE
            response.headers["Link"] = _LINK
            return response

        return _handler


router = APIRouter(prefix="/api/v1", route_class=_DeprecatedRoute)


@router.get("/recipes")
async def get_recipes_v1(
    search: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    return await _combined_search(search, store, external)


@router.get("/recipes/search")
async def search_recipes_v1(
    q: Optional[str] = None,
    search: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    return await _combined_search(q or search, store, external)


@router.get("/recipes/export")
def export_recipes_v1(store: RecipeStore = Depends(get_store)):
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse
    recipes = store.get_all_recipes()
    return JSONResponse(content=jsonable_encoder([r.model_dump() for r in recipes]))


@router.get("/recipes/external/{meal_id}")
async def get_external_recipe_v1(
    meal_id: str,
    response: Response,
    external: ExternalRecipeClient = Depends(get_external_client),
):
    try:
        with timed("external", "lookup") as timer:
            recipe = await external.get_by_id(meal_id)
    except ExternalAPIError as error:
        raise HTTPException(status_code=502, detail=str(error))
    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"External recipe '{meal_id}' not found")
    return recipe


@router.get("/recipes/{recipe_id}")
def get_recipe_v1(
    recipe_id: str,
    response: Response,
    store: RecipeStore = Depends(get_store),
):
    with timed("internal", "lookup") as timer:
        recipe = store.get_recipe(recipe_id)
    response.headers["X-Query-Time-Ms"] = f"{timer.duration_ms:.2f}"
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return recipe


@router.post("/recipes", status_code=200)
def create_recipe_v1(recipe: RecipeCreate, store: RecipeStore = Depends(get_store)):
    return store.create_recipe(recipe)


@router.put("/recipes/{recipe_id}")
def update_recipe_v1(
    recipe_id: str,
    recipe: RecipeUpdate,
    store: RecipeStore = Depends(get_store),
):
    updated = store.update_recipe(recipe_id, recipe)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return updated


@router.delete("/recipes/{recipe_id}")
def delete_recipe_v1(recipe_id: str, store: RecipeStore = Depends(get_store)):
    if not store.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")
    return {"message": "Recipe deleted successfully", "status": "success"}
