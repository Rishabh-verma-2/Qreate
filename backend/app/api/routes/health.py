"""Health check route."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.database.connection import get_db
from app.services.cloudinary.uploader import is_cloudinary_configured
from app.services.llm import configured_provider_names
from app.services.media.ffmpeg import ffmpeg_bin

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health_check():
    settings = get_settings()
    db = get_db()
    llm = configured_provider_names()
    stock = [n for n, k in (("pexels", settings.PEXELS_API_KEY), ("pixabay", settings.PIXABAY_API_KEY),
                            ("unsplash", settings.UNSPLASH_ACCESS_KEY)) if k]
    return {
        "status": "ok" if db is not None and llm and is_cloudinary_configured() else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db is not None else "not configured",
        "cloudinary": "configured" if is_cloudinary_configured() else "not configured",
        "llm_providers": llm,
        "stock_media_sources": stock or ["none — StockSnap photos + text cards only"],
        "ffmpeg": ffmpeg_bin(),
        "output": f"{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}@{settings.VIDEO_FPS}fps",
        "embedded_worker": settings.EMBEDDED_WORKER,
    }
