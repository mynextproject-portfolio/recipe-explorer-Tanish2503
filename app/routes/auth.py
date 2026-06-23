"""
Authentication and user-profile routes.
Rate-limited register and login: 5 requests/minute per IP.
"""

import sqlite3
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import UserStore, get_current_user, get_user_store
from app.middleware.rate_limit import limiter
from app.models_auth import FavoriteOut, Token, UserCreate, UserLogin, UserOut
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.user_storage import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: UserCreate,
    user_store: UserStore = Depends(get_user_store),
):
    try:
        user = user_store.create_user(
            email=body.email.lower(),
            username=body.username,
            password_hash=hash_password(body.password),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email or username already exists",
        )
    token = create_access_token(user.id, user.email, user.username)
    return Token(access_token=token, user=_user_out(user))


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: UserLogin,
    user_store: UserStore = Depends(get_user_store),
):
    user = user_store.get_user_by_email(body.email.lower())
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id, user.email, user.username)
    return Token(access_token=token, user=_user_out(user))


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


@router.get("/favorites", response_model=List[FavoriteOut])
def list_favorites(
    current_user: User = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
):
    favs = user_store.get_favorites(current_user.id)
    return [
        FavoriteOut(
            id=f.id,
            recipe_id=f.recipe_id,
            recipe_source=f.recipe_source,
            created_at=f.created_at,
        )
        for f in favs
    ]


@router.post("/favorites/{recipe_id}", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_favorite(
    recipe_id: str,
    source: Literal["internal", "external"] = "internal",
    current_user: User = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
):
    try:
        fav = user_store.add_favorite(current_user.id, recipe_id, source)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already in favorites",
        )
    return FavoriteOut(
        id=fav.id,
        recipe_id=fav.recipe_id,
        recipe_source=fav.recipe_source,
        created_at=fav.created_at,
    )


@router.delete("/favorites/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    recipe_id: str,
    source: Literal["internal", "external"] = "internal",
    current_user: User = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
):
    removed = user_store.remove_favorite(current_user.id, recipe_id, source)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in favorites")
