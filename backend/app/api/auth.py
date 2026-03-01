from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.player import PlayerResponse
from app.services.auth import AuthError, login, refresh_access_token, register

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=PlayerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_player(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        player = await register(db, body.username, body.email, body.password)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.detail,
        )
    return player


@router.post("/login", response_model=TokenResponse)
async def login_player(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        tokens = await login(db, body.email, body.password)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
        )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        tokens = await refresh_access_token(db, body.refresh_token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
        )
    return tokens