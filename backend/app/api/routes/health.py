"""Health check route."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.database.connection import get_db
from app.services.cloudinary.uploader import is_cloudinary_configured

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health_check():
    settings = get_settings()
    db = get_db()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database": "connected" if db is not None else "not configured",
        "cloudinary": "configured" if is_cloudinary_configured() else "not configured",
        "agnes": "configured" if settings.AGNES_API_KEY else "not configured",
        "agnes_video_model": settings.AGNES_VIDEO_MODEL,
        "agnes_chat_model": settings.AGNES_CHAT_MODEL,
    }
