from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List
import uuid

# Constants
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_CUISINE_LENGTH = 100
MAX_INGREDIENTS = 50
MAX_INSTRUCTIONS = 50
MAX_TAGS = 20


class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    cuisine: str = Field("", max_length=MAX_CUISINE_LENGTH)
    ingredients: List[str] = Field(..., min_length=1, max_length=MAX_INGREDIENTS)
    instructions: List[str] = Field(..., min_length=1, max_length=MAX_INSTRUCTIONS)
    tags: List[str] = Field(default_factory=list, max_length=MAX_TAGS)

    @field_validator("title", "description", "cuisine", mode="after")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("title", "description", mode="after")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("ingredients", "instructions", "tags", mode="after")
    @classmethod
    def clean_string_list(cls, items: List[str]) -> List[str]:
        return [item.strip() for item in items if item and item.strip()]

    @field_validator("ingredients", "instructions", mode="after")
    @classmethod
    def require_non_empty_list(cls, items: List[str]) -> List[str]:
        if not items:
            raise ValueError("must contain at least one non-empty item")
        return items


class Recipe(RecipeBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(RecipeBase):
    pass
