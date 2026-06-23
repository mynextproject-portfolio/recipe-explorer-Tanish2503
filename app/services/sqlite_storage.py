"""
SQLite-backed implementation of the RecipeStore protocol.

Each method opens its own connection so the object is safe to share across
FastAPI's thread-pool (sync endpoints run in threads). sqlite3's default
WAL mode is not enabled here, but can be added if write contention appears.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models import Recipe, RecipeCreate, RecipeUpdate

DEFAULT_DB_PATH = Path("recipes.db")


class SQLiteRecipeStorage:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    _V2_COLUMNS = [
        ("difficulty",           "TEXT"),
        ("prep_time_minutes",    "INTEGER"),
        ("cook_time_minutes",    "INTEGER"),
        ("servings",             "INTEGER"),
        ("nutritional_info",     "TEXT"),
        ("dietary_restrictions", "TEXT"),
        ("equipment",            "TEXT"),
        ("techniques",           "TEXT"),
        ("related_recipe_ids",   "TEXT"),
    ]

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    id          TEXT PRIMARY KEY,
                    title       TEXT NOT NULL,
                    description TEXT NOT NULL,
                    cuisine     TEXT NOT NULL DEFAULT '',
                    ingredients TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    tags        TEXT NOT NULL DEFAULT '[]',
                    source      TEXT NOT NULL DEFAULT 'internal',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
                """
            )
            # Idempotent schema migration: add v2 columns if missing
            existing = {row[1] for row in conn.execute("PRAGMA table_info(recipes)").fetchall()}
            for col_name, col_type in self._V2_COLUMNS:
                if col_name not in existing:
                    conn.execute(f"ALTER TABLE recipes ADD COLUMN {col_name} {col_type}")

    def _row_to_recipe(self, row: sqlite3.Row) -> Recipe:
        return Recipe(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            cuisine=row["cuisine"],
            ingredients=json.loads(row["ingredients"]),
            instructions=json.loads(row["instructions"]),
            tags=json.loads(row["tags"]),
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _insert(self, conn: sqlite3.Connection, recipe: Recipe) -> None:
        conn.execute(
            """
            INSERT INTO recipes
                (id, title, description, cuisine, ingredients, instructions,
                 tags, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe.id,
                recipe.title,
                recipe.description,
                recipe.cuisine,
                json.dumps(recipe.ingredients),
                json.dumps(recipe.instructions),
                json.dumps(recipe.tags),
                recipe.source,
                recipe.created_at.isoformat(),
                recipe.updated_at.isoformat(),
            ),
        )

    # ------------------------------------------------------------------
    # RecipeStore protocol
    # ------------------------------------------------------------------

    def get_all_recipes(self) -> List[Recipe]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recipes ORDER BY created_at"
            ).fetchall()
        return [self._row_to_recipe(r) for r in rows]

    def search_recipes(self, query: str) -> List[Recipe]:
        if not query:
            return self.get_all_recipes()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recipes WHERE LOWER(title) LIKE ? ORDER BY created_at",
                (f"%{query.lower()}%",),
            ).fetchall()
        return [self._row_to_recipe(r) for r in rows]

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
            ).fetchone()
        return self._row_to_recipe(row) if row else None

    def create_recipe(self, recipe_data: RecipeCreate) -> Recipe:
        recipe = Recipe(**recipe_data.model_dump())
        with self._connect() as conn:
            self._insert(conn, recipe)
        return recipe

    def update_recipe(
        self, recipe_id: str, recipe_data: RecipeUpdate
    ) -> Optional[Recipe]:
        if not self.get_recipe(recipe_id):
            return None

        updated_at = datetime.now()
        data = recipe_data.model_dump()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE recipes
                SET title=?, description=?, cuisine=?, ingredients=?,
                    instructions=?, tags=?, updated_at=?
                WHERE id=?
                """,
                (
                    data["title"],
                    data["description"],
                    data["cuisine"],
                    json.dumps(data["ingredients"]),
                    json.dumps(data["instructions"]),
                    json.dumps(data["tags"]),
                    updated_at.isoformat(),
                    recipe_id,
                ),
            )
        return self.get_recipe(recipe_id)

    def delete_recipe(self, recipe_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM recipes WHERE id = ?", (recipe_id,)
            )
        return cursor.rowcount > 0

    def import_recipes(self, recipes_data: List[dict]) -> dict:
        """Replace all existing recipes with validated entries from recipes_data."""
        valid: List[Recipe] = []
        errors: List[dict] = []

        for index, recipe_dict in enumerate(recipes_data):
            try:
                rd = dict(recipe_dict)
                if "created_at" in rd:
                    rd["created_at"] = datetime.fromisoformat(rd["created_at"])
                if "updated_at" in rd:
                    rd["updated_at"] = datetime.fromisoformat(rd["updated_at"])
                valid.append(Recipe(**rd))
            except Exception as error:
                errors.append({"index": index, "error": str(error)})

        with self._connect() as conn:
            conn.execute("DELETE FROM recipes")
            for recipe in valid:
                self._insert(conn, recipe)

        return {
            "imported": len(valid),
            "skipped": len(errors),
            "errors": errors,
        }
