"""Application configuration — loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "Qreate API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── CORS ───────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── MongoDB ────────────────────────────────────────────────────────────
    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = "qreate"

    # ── Cloudinary ─────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── Agnes AI ───────────────────────────────────────────────────────────
    AGNES_API_KEY: str = ""
    AGNES_BASE_URL: str = "https://apihub.agnes-ai.com"

    # Video generation
    AGNES_VIDEO_MODEL: str = "agnes-video-2.5-flash"
    AGNES_VIDEO_SIZE: str = "720P"

    # Script generation
    AGNES_CHAT_MODEL: str = "agnes-2.5-flash"

    # ── Polling ────────────────────────────────────────────────────────────
    VIDEO_POLL_INTERVAL_SECONDS: int = 10
    VIDEO_POLL_MAX_ATTEMPTS: int = 120   # 20 minutes max
    VIDEO_QUEUE_RETRY_MAX_SECONDS: int = 900  # 15 minutes for queue full

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
