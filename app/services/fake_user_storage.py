"""
In-memory UserStorage for tests. Mirrors FakeUserStorage / RecipeStorage pattern.
Tests inject this via app.dependency_overrides[get_user_store].
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.services.user_storage import Favorite, User


class FakeUserStorage:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._favorites: Dict[str, Favorite] = {}

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, email: str, username: str, password_hash: str) -> User:
        if any(u.email == email.lower() for u in self._users.values()):
            raise sqlite3.IntegrityError("UNIQUE constraint failed: users.email")
        if any(u.username == username for u in self._users.values()):
            raise sqlite3.IntegrityError("UNIQUE constraint failed: users.username")
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            username=username,
            password_hash=password_hash,
            created_at=datetime.utcnow().isoformat(),
        )
        self._users[user.id] = user
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        return next(
            (u for u in self._users.values() if u.email == email.lower()), None
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def _fav_key(self, user_id: str, recipe_id: str, recipe_source: str) -> Tuple:
        return (user_id, recipe_id, recipe_source)

    def get_favorites(self, user_id: str) -> List[Favorite]:
        return [f for f in self._favorites.values() if f.user_id == user_id]

    def add_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> Favorite:
        key = self._fav_key(user_id, recipe_id, recipe_source)
        if any(
            (f.user_id, f.recipe_id, f.recipe_source) == key
            for f in self._favorites.values()
        ):
            raise sqlite3.IntegrityError("UNIQUE constraint failed: favorites")
        fav = Favorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            recipe_id=recipe_id,
            recipe_source=recipe_source,
            created_at=datetime.utcnow().isoformat(),
        )
        self._favorites[fav.id] = fav
        return fav

    def remove_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool:
        key = self._fav_key(user_id, recipe_id, recipe_source)
        to_delete = [
            fid
            for fid, f in self._favorites.items()
            if (f.user_id, f.recipe_id, f.recipe_source) == key
        ]
        for fid in to_delete:
            del self._favorites[fid]
        return bool(to_delete)

    def is_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool:
        key = self._fav_key(user_id, recipe_id, recipe_source)
        return any(
            (f.user_id, f.recipe_id, f.recipe_source) == key
            for f in self._favorites.values()
        )
