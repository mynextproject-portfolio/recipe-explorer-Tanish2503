from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import (
    ExternalRecipeClient,
    RecipeStore,
    get_external_client,
    get_store,
)
from app.exceptions import ExternalAPIError
from app.models import RecipeCreate, RecipeUpdate
from app.services.metrics import timed

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    search: Optional[str] = None,
    message: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Home page with recipe list and search (internal recipes + external when searching)."""
    external_search_error = None

    if not search:
        with timed("internal", "list_all") as timer:
            recipes = store.get_all_recipes()
        timing = {"internal_ms": round(timer.duration_ms, 2)}
    else:
        with timed("internal", "search") as internal_timer:
            recipes = store.search_recipes(search)
        timing = {"internal_ms": round(internal_timer.duration_ms, 2)}

        try:
            with timed("external", "search") as external_timer:
                external_recipes = await external.search(search)
            recipes = recipes + external_recipes
            timing["external_ms"] = round(external_timer.duration_ms, 2)
        except ExternalAPIError as error:
            external_search_error = str(error)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "recipes": recipes,
            "search_query": search or "",
            "message": message,
            "external_search_error": external_search_error,
            "timing": timing,
        },
    )


@router.get("/recipes/new", response_class=HTMLResponse)
def new_recipe_form(request: Request):
    """New recipe form."""
    return templates.TemplateResponse(
        request, "recipe_form.html", {"recipe": None, "is_edit": False}
    )


@router.get("/recipes/external/{meal_id}", response_class=HTMLResponse)
async def external_recipe_detail(
    request: Request,
    meal_id: str,
    external: ExternalRecipeClient = Depends(get_external_client),
):
    """Recipe detail page for an external recipe."""
    try:
        recipe = await external.get_by_id(meal_id)
    except ExternalAPIError as error:
        raise HTTPException(status_code=502, detail=str(error))

    if not recipe:
        raise HTTPException(status_code=404, detail="External recipe not found")

    return templates.TemplateResponse(
        request, "recipe_detail.html", {"recipe": recipe, "message": None}
    )


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(
    request: Request,
    recipe_id: str,
    message: Optional[str] = None,
    store: RecipeStore = Depends(get_store),
):
    """Recipe detail page."""
    recipe = store.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return templates.TemplateResponse(
        request, "recipe_detail.html", {"recipe": recipe, "message": message}
    )


@router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def edit_recipe_form(
    request: Request,
    recipe_id: str,
    store: RecipeStore = Depends(get_store),
):
    """Edit recipe form."""
    recipe = store.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return templates.TemplateResponse(
        request, "recipe_form.html", {"recipe": recipe, "is_edit": True}
    )


@router.post("/recipes/new")
def create_recipe_form(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    cuisine: str = Form(""),
    ingredients: str = Form(...),
    instructions: str = Form(...),
    tags: str = Form(...),
    store: RecipeStore = Depends(get_store),
):
    """Handle new recipe form submission."""
    try:
        if len(title) > 200:
            raise ValueError("Title too long")

        ingredient_list = [ing.strip() for ing in ingredients.split("\n") if ing.strip()]
        step_list = [step.strip() for step in instructions.split("\n") if step.strip()]
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        if not ingredient_list:
            raise ValueError("At least one ingredient required")
        if not step_list:
            raise ValueError("Instructions are required")

        recipe_data = RecipeCreate(
            title=title,
            description=description,
            cuisine=cuisine.strip(),
            ingredients=ingredient_list,
            instructions=step_list,
            tags=tag_list,
        )

        new_recipe = store.create_recipe(recipe_data)
        return RedirectResponse(
            url=f"/recipes/{new_recipe.id}?message=Recipe created successfully",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/?message=Error creating recipe: {str(e)}", status_code=303
        )


@router.post("/recipes/{recipe_id}/edit")
def update_recipe_form(
    request: Request,
    recipe_id: str,
    title: str = Form(...),
    description: str = Form(...),
    cuisine: str = Form(""),
    ingredients: str = Form(...),
    instructions: str = Form(...),
    tags: str = Form(...),
    store: RecipeStore = Depends(get_store),
):
    """Handle edit recipe form submission."""
    try:
        if len(title) > 200:
            raise ValueError("Title is too long!")

        ingredient_list = [ing.strip() for ing in ingredients.split("\n") if ing.strip()]
        step_list = [step.strip() for step in instructions.split("\n") if step.strip()]
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        if not ingredient_list:
            raise ValueError("Need ingredients!")
        if not step_list:
            raise ValueError("Instructions are required")

        recipe_data = RecipeUpdate(
            title=title,
            description=description,
            cuisine=cuisine.strip(),
            ingredients=ingredient_list,
            instructions=step_list,
            tags=tag_list,
        )

        updated = store.update_recipe(recipe_id, recipe_data)
        if not updated:
            return RedirectResponse(url="/?message=Recipe not found", status_code=303)

        return RedirectResponse(
            url=f"/recipes/{recipe_id}?message=Recipe updated successfully",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/recipes/{recipe_id}?message=Error updating recipe: {str(e)}",
            status_code=303,
        )


@router.post("/recipes/{recipe_id}/delete")
def delete_recipe_form(
    recipe_id: str,
    store: RecipeStore = Depends(get_store),
):
    """Handle recipe deletion."""
    if store.delete_recipe(recipe_id):
        return RedirectResponse(
            url="/?message=Recipe deleted successfully", status_code=303
        )
    return RedirectResponse(url="/?message=Recipe not found", status_code=303)


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, message: Optional[str] = None):
    """Import recipes page."""
    return templates.TemplateResponse(request, "import.html", {"message": message})
