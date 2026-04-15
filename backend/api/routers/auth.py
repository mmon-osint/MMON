"""
MMON — Auth router: login, profilo, setup password.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..middleware.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ...models.db_models import User
from ...models.schemas import (
    SetupPasswordRequest,
    TokenRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(body: TokenRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Autenticazione utente → JWT token."""
    result = await db.execute(
        select(User).where(User.username == body.username, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide",
        )

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Profilo utente corrente."""
    return UserResponse.model_validate(user)


@router.post("/setup-password")
async def setup_password(
    body: SetupPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Setup password admin al primo avvio.
    Funziona solo se la password è ancora il placeholder del wizard.
    """
    result = await db.execute(
        select(User).where(User.username == "admin")
    )
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Admin user non trovato")

    if admin.password_hash != "TO_BE_SET_BY_WIZARD":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password già impostata",
        )

    admin.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "Password admin impostata con successo"}
