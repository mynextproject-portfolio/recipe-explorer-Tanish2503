"""
Dependency injection contracts and provider functions.

Protocols define the shape expected by routes; provider functions return the
default singleton implementations. Tests override providers via
``app.dependency_overrides[get_store] = lambda: FakeStore()``.
"""

import os
from pathlib import Path
from typing import List, Optional, Protocol

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.services.metrics import TimingMetrics
from app.services.metrics import metrics as _metrics_instance
from app.services.sqlite_storage import SQLiteRecipeStorage
from app.services.themealdb import MealDBClient
from app.services.user_storage import Favorite, SQLiteUserStorage, User

# ---------------------------------------------------------------------------
# Recipe store
# ---------------------------------------------------------------------------


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


_db_path = Path(os.getenv("DB_PATH", "recipes.db"))
_sqlite_storage = SQLiteRecipeStorage(db_path=_db_path)


def get_store() -> RecipeStore:
    return _sqlite_storage


def get_external_client() -> ExternalRecipeClient:
    return MealDBClient()


def get_metrics() -> TimingMetrics:
    return _metrics_instance


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------


class UserStore(Protocol):
    def create_user(self, email: str, username: str, password_hash: str) -> User: ...

    def get_user_by_email(self, email: str) -> Optional[User]: ...

    def get_user_by_id(self, user_id: str) -> Optional[User]: ...

    def get_favorites(self, user_id: str) -> List[Favorite]: ...

    def add_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> Favorite: ...

    def remove_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool: ...

    def is_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool: ...


_sqlite_user_storage = SQLiteUserStorage(db_path=_db_path)


def get_user_store() -> UserStore:
    return _sqlite_user_storage


# ---------------------------------------------------------------------------
# Auth: current user dependency
# ---------------------------------------------------------------------------

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(_oauth2_scheme),
    user_store: UserStore = Depends(get_user_store),
) -> User:
    from app.services.auth import decode_access_token

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exc
    user = user_store.get_user_by_id(payload["sub"])
    if not user:
        raise credentials_exc
    return user


def get_optional_user(
    token: Optional[str] = Depends(_oauth2_scheme),
    user_store: UserStore = Depends(get_user_store),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising 401."""
    if not token:
        return None
    from app.services.auth import decode_access_token

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return user_store.get_user_by_id(payload["sub"])
