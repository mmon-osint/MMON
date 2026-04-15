"""
MMON — FastAPI main application.
"""
from __future__ import annotations

import time

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .routers import auth, findings, jobs, widgets
from ..models.schemas import HealthResponse

settings = get_settings()
logger = structlog.get_logger(__name__)

# ── Rate limiter ──
limiter = Limiter(key_func=get_remote_address)

# ── App ──
app = FastAPI(
    title="MMON API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringere in produzione
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """Log ogni richiesta con durata."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
        client=request.client.host if request.client else "unknown",
    )
    return response


# ── Content-Type check middleware ──
@app.middleware("http")
async def check_content_type(request: Request, call_next) -> Response:
    """Rifiuta body non-JSON su endpoint API (esclusi GET e health)."""
    if (
        request.method in ("POST", "PUT", "PATCH")
        and request.url.path.startswith("/api/")
        and request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        return Response(
            content='{"detail":"Content-Type must be application/json"}',
            status_code=415,
            media_type="application/json",
        )
    return await call_next(request)


# ── Routers (prefisso /api/v1) ──
app.include_router(auth.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(widgets.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")


# ── Health (pubblico) ──
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Health check — unico endpoint non autenticato."""
    db_status = "unknown"
    redis_status = "unknown"

    # Check DB
    try:
        from .database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    # Check Redis
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(settings.redis_url)
        r.ping()
        db_status_redis = "ok"
        r.close()
        redis_status = "ok"
    except Exception:
        redis_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        version="1.0.0",
        database=db_status,
        redis=redis_status,
    )


# ── API key test endpoint (per wizard) ──
@app.post("/api/v1/test-apikey", tags=["system"])
@limiter.limit("10/minute")
async def test_api_key(request: Request, body: dict) -> dict:
    """Test validità API key. Usato dal wizard (step 6)."""
    provider = body.get("provider", "")
    key = body.get("key", "")

    if not key:
        return {"valid": False, "error": "Key vuota"}

    if provider == "shodan":
        try:
            import httpx
            resp = await httpx.AsyncClient().get(
                f"https://api.shodan.io/api-info?key={key}",
                timeout=10,
            )
            return {"valid": resp.status_code == 200}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    elif provider == "criminal_ip":
        try:
            import httpx
            resp = await httpx.AsyncClient().get(
                "https://api.criminalip.io/v1/user/me",
                headers={"x-api-key": key},
                timeout=10,
            )
            return {"valid": resp.status_code == 200}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    return {"valid": False, "error": f"Provider '{provider}' non supportato per test"}


# ── Missing import fix ──
from sqlalchemy import text


# ── Startup / Shutdown ──
@app.on_event("startup")
async def startup():
    logger.info("mmon_api.startup", version="1.0.0", mode=settings.deploy_mode)


@app.on_event("shutdown")
async def shutdown():
    logger.info("mmon_api.shutdown")
