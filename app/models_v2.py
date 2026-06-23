"""
v2 Recipe models — extends the v1 schema with nutritional info, difficulty,
dietary restrictions, equipment, techniques, and related recipes.

v1 clients (GET /api/recipes or GET /api/v1/recipes) receive Recipe objects
with no v2 fields. v2 clients receive RecipeV2 objects with all fields.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models import RecipeBase


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class DietaryRestriction(str, Enum):
    vegetarian = "vegetarian"
    vegan = "vegan"
    gluten_free = "gluten_free"
    dairy_free = "dairy_free"
    nut_free = "nut_free"
    halal = "halal"
    kosher = "kosher"
    low_carb = "low_carb"


class SortOrder(str, Enum):
    created_asc = "created_asc"
    created_desc = "created_desc"
    title_asc = "title_asc"
    title_desc = "title_desc"
    difficulty_asc = "difficulty_asc"
    difficulty_desc = "difficulty_desc"


class NutritionalInfo(BaseModel):
    calories: Optional[int] = Field(None, ge=0, le=10_000)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)
    fiber_g: Optional[float] = Field(None, ge=0)


_DIFFICULTY_ORDER = {
    None: -1,
    Difficulty.beginner: 0,
    Difficulty.intermediate: 1,
    Difficulty.advanced: 2,
    Difficulty.expert: 3,
}


class RecipeBaseV2(RecipeBase):
    difficulty: Optional[Difficulty] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0, le=1440)
    cook_time_minutes: Optional[int] = Field(None, ge=0, le=1440)
    servings: Optional[int] = Field(None, ge=1, le=100)
    nutritional_info: Optional[NutritionalInfo] = None
    dietary_restrictions: List[DietaryRestriction] = Field(default_factory=list)
    equipment: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    related_recipe_ids: List[str] = Field(default_factory=list)


class RecipeV2(RecipeBaseV2):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Literal["internal", "external"] = "internal"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecipeCreateV2(RecipeBaseV2):
    pass


class RecipeUpdateV2(RecipeBaseV2):
    pass


class BulkCreateRequest(BaseModel):
    recipes: List[RecipeCreateV2] = Field(..., min_length=1, max_length=50)


class BulkCreateResponse(BaseModel):
    created: List[RecipeV2]
    errors: List[dict]
    total_requested: int
