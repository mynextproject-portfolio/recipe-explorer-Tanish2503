import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.dependencies import get_store
from app.routes import api
from app.services.cache import recipe_cache, REDIS_URL_DEFAULT

APP_NAME = "Recipe Explorer"
VERSION = "1.0.0"
DEBUG = True

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

SAMPLE_DATA_PATH = Path(__file__).parent.parent / "sample-recipes.json"
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis, load sample recipes, then clean up on shutdown."""
    redis_url = os.getenv("REDIS_URL", REDIS_URL_DEFAULT)
    await recipe_cache.connect(redis_url)

    store = get_store()
    if not store.get_all_recipes() and SAMPLE_DATA_PATH.exists():
        try:
            with open(SAMPLE_DATA_PATH, "r", encoding="utf-8") as sample_file:
                recipes_data = json.load(sample_file)
            result = store.import_recipes(recipes_data)
            print(f"Seeded {result['imported']} recipes from {SAMPLE_DATA_PATH.name}")
        except Exception as error:
            print(f"Failed to seed sample data: {error}")

    yield

    await recipe_cache.close()


app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)

# Legacy static files (CSS/JS used by Jinja2 templates)
app.mount("/static", StaticFiles(directory="static"), name="static")

# React frontend built assets
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="react-assets")

# API routes
app.include_router(api.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": "Validation failed", "errors": errors}
    )


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve the React SPA for all non-API routes."""
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse(
        status_code=503,
        content={"detail": "Frontend not built. Run: cd frontend && npm run build"},
    )
