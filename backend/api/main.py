"""
MMON — FastAPI Application entrypoint
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.config import get_settings
from api.routers import auth, findings, jobs, widgets
from models.schemas import HealthResponse

# Logging strutturato
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# App
app = FastAPI(
    title="MMON API",
    description="Morpheus MONitoring — Backend API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrittivo in produzione
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{settings.backend_ip}",
        f"https://{settings.backend_ip}",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# =============================================================
# MIDDLEWARE: request logging
# =============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log ogni request con metodo, path e status code."""
    response = await call_next(request)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        client=request.client.host if request.client else "unknown",
    )
    return response


# =============================================================
# MIDDLEWARE: input sanitization header check
# =============================================================

@app.middleware("http")
async def check_content_type(request: Request, call_next):
    """Rifiuta request POST/PUT senza Content-Type JSON appropriato."""
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        if content_type and "json" not in content_type and "form" not in content_type:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": "Content-Type deve essere application/json"},
            )
    return await call_next(request)


# =============================================================
# ROUTERS
# =============================================================

app.include_router(auth.router)
app.include_router(findings.router)
app.include_router(widgets.router)
app.include_router(jobs.router)


# =============================================================
# HEALTH CHECK (pubblico, unico endpoint senza auth)
# =============================================================

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Health check — unico endpoint pubblico senza autenticazione."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        mode=settings.mode,
    )


# =============================================================
# STARTUP / SHUTDOWN
# =============================================================

@app.on_event("startup")
async def startup():
    logger.info("mmon_api_start", mode=settings.mode, version="0.1.0")


@app.on_event("shutdown")
async def shutdown():
    logger.info("mmon_api_shutdown")
