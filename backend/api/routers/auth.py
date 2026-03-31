"""
MMON — Auth router: login, token refresh, user info.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_db
from api.middleware.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from models.db_models import User
from models.schemas import TokenRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: TokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Autenticazione utente con username e password.
    Restituisce un JWT access token.
    """
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabilitato",
        )

    settings = get_settings()
    token = create_access_token(
        user_id=str(user.user_id),
        username=user.username,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """Restituisce informazioni sull'utente corrente."""
    return UserResponse.model_validate(user)


@router.post("/setup-password", response_model=UserResponse)
async def setup_initial_password(
    body: TokenRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Imposta la password iniziale per l'utente admin creato dal wizard.
    Funziona solo se la password attuale è il placeholder 'TO_BE_SET_BY_WIZARD'.
    """
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato",
        )

    if user.password_hash != "TO_BE_SET_BY_WIZARD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password già impostata. Usa /auth/login.",
        )

    user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)
