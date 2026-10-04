"""FastAPI application entry point."""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import QreateError, qreate_exception_handler, generic_exception_handler
from app.database.connection import connect_db, close_db, get_db
from app.api.routes import auth, health, pipeline, projects, scripts, uploads, videos
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
cors_origins = [
    *settings.cors_origins,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
if "*" in cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Local dev on any port + deployed previews (CORS_ORIGIN_REGEX, e.g. *.vercel.app)
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    + (f"|{settings.CORS_ORIGIN_REGEX}" if settings.CORS_ORIGIN_REGEX else ""),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ─────────────────────────────────────────────────────────
app.add_exception_handler(QreateError, qreate_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Lifecycle ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
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


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "docs": "/docs", "health": "/api/health"}
