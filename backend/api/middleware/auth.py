"""
MMON — JWT Authentication middleware e utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_db
from models.db_models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash una password con bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica password plain vs hash bcrypt."""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Genera un JWT access token.

    Args:
        user_id: UUID dell'utente come stringa
        username: username dell'utente
        role: ruolo (admin, analyst, viewer)
        expires_delta: durata custom del token

    Returns:
        Token JWT firmato
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """
    Decodifica e valida un JWT token.

    Args:
        token: JWT string

    Returns:
        Payload decodificato

    Raises:
        HTTPException 401 se token invalido o scaduto
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token non valido: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency FastAPI: estrae e valida l'utente dal JWT token.

    Returns:
        Oggetto User dal database

    Raises:
        HTTPException 401 se token mancante, invalido, o utente non trovato
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalido",
        )

    result = await db.execute(
        select(User).where(User.user_id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabilitato",
        )

    return user


def require_role(required_role: str):
    """
    Factory per dependency che verifica il ruolo utente.

    Args:
        required_role: ruolo minimo richiesto (admin > analyst > viewer)

    Returns:
        Dependency function
    """
    role_hierarchy = {"viewer": 0, "analyst": 1, "admin": 2}

    async def check_role(user: User = Depends(get_current_user)) -> User:
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Ruolo '{required_role}' richiesto. Ruolo attuale: '{user.role}'",
            )
        return user

    return check_role


async def authenticate_vm(
    request: Request,
) -> str:
    """
    Autenticazione per le VM (API key o IP whitelist).
    Le VM usano un header X-VM-Token per autenticarsi.

    Returns:
        Nome della VM autenticata (vm1, vm2, vm3)

    Raises:
        HTTPException 401 se non autenticata
    """
    settings = get_settings()

    # Verificare IP whitelist
    client_ip = request.client.host if request.client else None
    allowed_ips = [
        settings.vm1_ip,
        settings.vm2_ip,
        settings.vm3_ip,
        "127.0.0.1",
        "::1",
    ]
    allowed_ips = [ip for ip in allowed_ips if ip]

    if client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"IP {client_ip} non autorizzato",
        )

    # Determinare quale VM sta chiamando
    vm_header = request.headers.get("X-VM-Name", "")
    if vm_header not in ("vm1", "vm2", "vm3"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-VM-Name mancante o invalido",
        )

    return vm_header
