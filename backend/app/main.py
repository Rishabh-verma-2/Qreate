"""FastAPI application entry point."""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import QreateError, qreate_exception_handler, generic_exception_handler
from app.database.connection import connect_db, close_db, get_db
from app.api.routes import auth, health, pipeline, projects, scripts, uploads, videos, voices
from app.services.media import vision
from app.services.media.http import close_client
from app.worker.runner import start_embedded_pool, stop_embedded_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Qreate — AI Video Generation Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Production: only the deployed frontend (FRONTEND_URL / EXTRA_CORS_ORIGINS / CORS_ORIGIN_REGEX).
# Development: also any localhost port.
cors_origins = list(settings.cors_origins)
if not settings.ALLOW_LOCALHOST_CORS:
    cors_origins = [o for o in cors_origins if "localhost" not in o and "127.0.0.1" not in o]
origin_regex = "|".join(filter(None, [
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.ALLOW_LOCALHOST_CORS else "",
    settings.CORS_ORIGIN_REGEX,
])) or None

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ─────────────────────────────────────────────────────────
app.add_exception_handler(QreateError, qreate_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Lifecycle ──────────────────────────────────────────────────────────────────
DEFAULT_JWT_SECRET = "qreate-jwt-secret-key-super-secure-token-2026"


@app.on_event("startup")
async def startup():
    secret = settings.JWT_SECRET_KEY or ""
    if settings.ENVIRONMENT == "production" and (secret == DEFAULT_JWT_SECRET or len(secret) < 32):
        # The default key is public in the repo — anyone could forge login tokens with it
        raise RuntimeError("Set JWT_SECRET_KEY to a private random value (32+ chars) before running in production")
    await connect_db()
    if settings.EMBEDDED_WORKER and get_db() is not None:
        start_embedded_pool()
        asyncio.create_task(vision.warm_up())


@app.on_event("shutdown")
async def shutdown():
    await stop_embedded_pool()
    await close_client()
    await close_db()


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(scripts.router)
app.include_router(videos.router)
app.include_router(pipeline.router)
app.include_router(uploads.router)
app.include_router(voices.router)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "docs": "/docs", "health": "/api/health"}
