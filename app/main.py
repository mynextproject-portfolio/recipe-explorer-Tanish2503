import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.routes import api, pages
from app.services.cache import recipe_cache, REDIS_URL_DEFAULT
from app.services.storage import recipe_storage

# App configuration
APP_NAME = "Recipe Explorer"
VERSION = "1.0.0"
DEBUG = True

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

SAMPLE_DATA_PATH = Path(__file__).parent.parent / "sample-recipes.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis, load sample recipes, then clean up on shutdown."""
    redis_url = os.getenv("REDIS_URL", REDIS_URL_DEFAULT)
    await recipe_cache.connect(redis_url)

    if not SAMPLE_DATA_PATH.exists():
        print(f"No sample data file found at {SAMPLE_DATA_PATH}")
    else:
        try:
            with open(SAMPLE_DATA_PATH, "r", encoding="utf-8") as sample_file:
                recipes_data = json.load(sample_file)
            result = recipe_storage.import_recipes(recipes_data)
            print(f"Seeded {result['imported']} recipes from {SAMPLE_DATA_PATH.name}")
        except Exception as error:
            print(f"Failed to seed sample data: {error}")

    yield

    await recipe_cache.close()


# Create FastAPI app
app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(api.router)
app.include_router(pages.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a concise field -> message breakdown instead of Pydantic's raw error objects."""
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


# Basic health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# @app.get("/status")
# def status():
#     return {"status": "ok", "version": "1.0.0"}
