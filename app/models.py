from pydantic import BaseModel, Field
from datetime import datetime
from typing import List
import uuid

# Constants
MAX_TITLE_LENGTH = 200
MAX_INGREDIENTS = 50

class Recipe(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    cuisine: str = ""
    ingredients: List[str]
    instructions: List[str]
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecipeCreate(BaseModel):
    title: str
    description: str
    cuisine: str = ""
    ingredients: List[str]
    instructions: List[str]
    tags: List[str] = Field(default_factory=list)


class RecipeUpdate(BaseModel):
    title: str
    description: str
    cuisine: str = ""
    ingredients: List[str]
    instructions: List[str]
    tags: List[str]
