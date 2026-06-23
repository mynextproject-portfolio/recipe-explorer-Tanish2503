"""
v2 SQLite storage — extends SQLiteRecipeStorage with the additional columns
introduced in the v2 schema (difficulty, nutritional_info, dietary_restrictions,
equipment, techniques, prep/cook time, servings, related_recipe_ids).

The parent class handles the v2 column migration in _init_db so the table is
always schema-complete regardless of which storage class is instantiated first.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.models_v2 import (
    Difficulty,
    DietaryRestriction,
    NutritionalInfo,
    RecipeCreateV2,
    RecipeUpdateV2,
    RecipeV2,
    SortOrder,
)
from app.services.sqlite_storage import SQLiteRecipeStorage

_V1_FIELDS = set(Recipe.model_fields.keys())

_SORT_SQL: dict[str, str] = {
    SortOrder.created_asc: "created_at ASC",
    SortOrder.created_desc: "created_at DESC",
    SortOrder.title_asc: "LOWER(title) ASC",
    SortOrder.title_desc: "LOWER(title) DESC",
    SortOrder.difficulty_asc: "CASE difficulty WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 WHEN 'advanced' THEN 2 WHEN 'expert' THEN 3 ELSE -1 END ASC, created_at ASC",
    SortOrder.difficulty_desc: "CASE difficulty WHEN 'expert' THEN 0 WHEN 'advanced' THEN 1 WHEN 'intermediate' THEN 2 WHEN 'beginner' THEN 3 ELSE 99 END ASC, created_at DESC",
}


class SQLiteRecipeStorageV2(SQLiteRecipeStorage):
    """Superset of SQLiteRecipeStorage that reads and writes v2 fields."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_recipe_v2(self, row: sqlite3.Row) -> RecipeV2:
        nutritional_raw = row["nutritional_info"]
        nutritional = NutritionalInfo(**json.loads(nutritional_raw)) if nutritional_raw else None

        dietary_raw = row["dietary_restrictions"]
        dietary = [DietaryRestriction(d) for d in json.loads(dietary_raw)] if dietary_raw else []

        return RecipeV2(
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
            difficulty=Difficulty(row["difficulty"]) if row["difficulty"] else None,
            prep_time_minutes=row["prep_time_minutes"],
            cook_time_minutes=row["cook_time_minutes"],
            servings=row["servings"],
            nutritional_info=nutritional,
            dietary_restrictions=dietary,
            equipment=json.loads(row["equipment"]) if row["equipment"] else [],
            techniques=json.loads(row["techniques"]) if row["techniques"] else [],
            related_recipe_ids=json.loads(row["related_recipe_ids"]) if row["related_recipe_ids"] else [],
        )

    def _insert_v2(self, conn: sqlite3.Connection, recipe: RecipeV2) -> None:
        conn.execute(
            """
            INSERT INTO recipes (
                id, title, description, cuisine, ingredients, instructions,
                tags, source, created_at, updated_at,
                difficulty, prep_time_minutes, cook_time_minutes, servings,
                nutritional_info, dietary_restrictions, equipment, techniques,
                related_recipe_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                recipe.difficulty.value if recipe.difficulty else None,
                recipe.prep_time_minutes,
                recipe.cook_time_minutes,
                recipe.servings,
                recipe.nutritional_info.model_dump_json() if recipe.nutritional_info else None,
                json.dumps([d.value for d in recipe.dietary_restrictions]),
                json.dumps(recipe.equipment),
                json.dumps(recipe.techniques),
                json.dumps(recipe.related_recipe_ids),
            ),
        )

    # ------------------------------------------------------------------
    # v2 RecipeStoreV2 protocol
    # ------------------------------------------------------------------

    def get_all_recipes_v2(self) -> List[RecipeV2]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM recipes ORDER BY created_at").fetchall()
        return [self._row_to_recipe_v2(r) for r in rows]

    def get_recipe_v2(self, recipe_id: str) -> Optional[RecipeV2]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
            ).fetchone()
        return self._row_to_recipe_v2(row) if row else None

    def search_recipes_v2(
        self,
        query: Optional[str] = None,
        cuisine: Optional[str] = None,
        difficulty: Optional[str] = None,
        dietary: Optional[str] = None,
        sort: SortOrder = SortOrder.created_desc,
    ) -> List[RecipeV2]:
        conditions: list[str] = []
        params: list = []

        if query:
            conditions.append(
                "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
            )
            q = f"%{query.lower()}%"
            params.extend([q, q, q])

        if cuisine:
            conditions.append("LOWER(cuisine) = LOWER(?)")
            params.append(cuisine)

        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        if dietary:
            # JSON array contains the value as a quoted string
            conditions.append("dietary_restrictions LIKE ?")
            params.append(f'%"{dietary}"%')

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order = _SORT_SQL.get(sort, "created_at DESC")

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM recipes {where} ORDER BY {order}"
            , params).fetchall()

        return [self._row_to_recipe_v2(r) for r in rows]

    def get_recipes_by_ids(self, ids: List[str]) -> List[RecipeV2]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM recipes WHERE id IN ({placeholders})", ids
            ).fetchall()
        by_id = {r["id"]: self._row_to_recipe_v2(r) for r in rows}
        # Preserve request order
        return [by_id[i] for i in ids if i in by_id]

    def create_recipe_v2(self, data: RecipeCreateV2) -> RecipeV2:
        recipe = RecipeV2(**data.model_dump())
        with self._connect() as conn:
            self._insert_v2(conn, recipe)
        return recipe

    def update_recipe_v2(
        self, recipe_id: str, data: RecipeUpdateV2
    ) -> Optional[RecipeV2]:
        if not self.get_recipe(recipe_id):
            return None

        updated_at = datetime.now()
        d = data.model_dump()
        nutritional = d.get("nutritional_info")
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE recipes
                SET title=?, description=?, cuisine=?, ingredients=?,
                    instructions=?, tags=?, updated_at=?,
                    difficulty=?, prep_time_minutes=?, cook_time_minutes=?,
                    servings=?, nutritional_info=?, dietary_restrictions=?,
                    equipment=?, techniques=?, related_recipe_ids=?
                WHERE id=?
                """,
                (
                    d["title"],
                    d["description"],
                    d["cuisine"],
                    json.dumps(d["ingredients"]),
                    json.dumps(d["instructions"]),
                    json.dumps(d["tags"]),
                    updated_at.isoformat(),
                    d["difficulty"].value if d.get("difficulty") else None,
                    d.get("prep_time_minutes"),
                    d.get("cook_time_minutes"),
                    d.get("servings"),
                    NutritionalInfo(**nutritional).model_dump_json() if nutritional else None,
                    json.dumps([dr.value if hasattr(dr, "value") else dr for dr in (d.get("dietary_restrictions") or [])]),
                    json.dumps(d.get("equipment") or []),
                    json.dumps(d.get("techniques") or []),
                    json.dumps(d.get("related_recipe_ids") or []),
                    recipe_id,
                ),
            )
        return self.get_recipe_v2(recipe_id)

    def bulk_create_v2(
        self, recipes: List[RecipeCreateV2]
    ) -> tuple[List[RecipeV2], List[dict]]:
        created: List[RecipeV2] = []
        errors: List[dict] = []
        for i, data in enumerate(recipes):
            try:
                created.append(self.create_recipe_v2(data))
            except Exception as exc:
                errors.append({"index": i, "error": str(exc)})
        return created, errors
