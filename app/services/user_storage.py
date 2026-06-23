"""
SQLite-backed user and favorites storage.
Same per-method connection pattern as sqlite_storage.py.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = Path("recipes.db")


class User:
    __slots__ = ("id", "email", "username", "password_hash", "created_at")

    def __init__(
        self,
        id: str,
        email: str,
        username: str,
        password_hash: str,
        created_at: str,
    ) -> None:
        self.id = id
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at


class Favorite:
    __slots__ = ("id", "user_id", "recipe_id", "recipe_source", "created_at")

    def __init__(
        self,
        id: str,
        user_id: str,
        recipe_id: str,
        recipe_source: str,
        created_at: str,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.recipe_id = recipe_id
        self.recipe_source = recipe_source
        self.created_at = created_at


class SQLiteUserStorage:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            TEXT PRIMARY KEY,
                    email         TEXT NOT NULL UNIQUE,
                    username      TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    id            TEXT PRIMARY KEY,
                    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    recipe_id     TEXT NOT NULL,
                    recipe_source TEXT NOT NULL CHECK(recipe_source IN ('internal', 'external')),
                    created_at    TEXT NOT NULL,
                    UNIQUE(user_id, recipe_id, recipe_source)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)"
            )

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            username=row["username"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )

    def create_user(self, email: str, username: str, password_hash: str) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            password_hash=password_hash,
            created_at=datetime.utcnow().isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (id, email, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.email, user.username, user.password_hash, user.created_at),
            )
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return self._row_to_user(row) if row else None

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def get_favorites(self, user_id: str) -> List[Favorite]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM favorites WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            Favorite(
                id=r["id"],
                user_id=r["user_id"],
                recipe_id=r["recipe_id"],
                recipe_source=r["recipe_source"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def add_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> Favorite:
        fav = Favorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            recipe_id=recipe_id,
            recipe_source=recipe_source,
            created_at=datetime.utcnow().isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO favorites (id, user_id, recipe_id, recipe_source, created_at) VALUES (?, ?, ?, ?, ?)",
                (fav.id, fav.user_id, fav.recipe_id, fav.recipe_source, fav.created_at),
            )
        return fav

    def remove_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND recipe_id = ? AND recipe_source = ?",
                (user_id, recipe_id, recipe_source),
            )
        return cursor.rowcount > 0

    def is_favorite(self, user_id: str, recipe_id: str, recipe_source: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND recipe_id = ? AND recipe_source = ?",
                (user_id, recipe_id, recipe_source),
            ).fetchone()
        return row is not None
