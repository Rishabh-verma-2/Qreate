"""Application configuration — loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "Qreate API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"   # "production" enables strict checks (JWT secret, CORS)

    # ── CORS ───────────────────────────────────────────────────────────────
    # Primary frontend URL plus optional comma-separated extras (e.g. Vercel previews)
    FRONTEND_URL: str = "http://localhost:5173"
    EXTRA_CORS_ORIGINS: str = ""
    # Regex for preview deployments, e.g. https://qreate-.*\.vercel\.app
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"
    ALLOW_LOCALHOST_CORS: bool = True     # set false in production

    # ── Abuse limits ───────────────────────────────────────────────────────
    RATE_LIMIT_VIDEOS_PER_HOUR: int = 10
    RATE_LIMIT_SCRIPTS_PER_HOUR: int = 20
    TOPIC_MAX_CHARS: int = 500

    # ── MongoDB ────────────────────────────────────────────────────────────
    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = "qreate"

    # ── Cloudinary ─────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── LLM providers (all OpenAI-compatible, tried in LLM_PROVIDER_ORDER) ─
    LLM_PROVIDER_ORDER: str = "groq,openrouter,gemini,agnes,ollama"
    LLM_TIMEOUT_SECONDS: int = 60

    # Groq — free tier, open-weight Llama models
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # OpenRouter — free open-weight models (":free" suffix)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Google Gemini — free tier via OpenAI-compatible endpoint
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Ollama — self-hosted open-source models
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "llama3.1"

    # Agnes AI (legacy provider, still usable for chat)
    AGNES_API_KEY: str = ""
    AGNES_BASE_URL: str = "https://apihub.agnes-ai.com"
    AGNES_CHAT_MODEL: str = "agnes-2.5-flash"
    AGNES_VIDEO_MODEL: str = "agnes-video-2.5-flash"
    AGNES_VIDEO_SIZE: str = "720P"
    AGNES_IMAGE_MODEL: str = "agnes-image-2.5-flash"

    # Legacy Agnes video engine polling (used by the purffle/free/agnes engines)
    VIDEO_POLL_INTERVAL_SECONDS: int = 10
    VIDEO_POLL_MAX_ATTEMPTS: int = 120
    VIDEO_QUEUE_RETRY_MAX_SECONDS: int = 900

    # ── Free stock media (real footage — keeps videos from looking AI-made) ─
    PEXELS_API_KEY: str = ""
    PIXABAY_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""

    # ── Trend research ─────────────────────────────────────────────────────
    RESEARCH_ENABLED: bool = True
    TREND_REGION: str = "IN"          # Google Trends / News / YouTube region
    YOUTUBE_API_KEY: str = ""         # optional: top-performing recent Shorts

    # ── Visual matching (CLIP looks at candidate thumbnails) ───────────────
    VISUAL_RERANK: bool = True
    CLIP_MODEL: str = "ViT-B-32"
    CLIP_PRETRAINED: str = "laion2b_s34b_b79k"
    RERANK_MIN_SCORE: float = 0.22   # below this the scene becomes a text card

    # ── Render settings ────────────────────────────────────────────────────
    VIDEO_WIDTH: int = 1080
    VIDEO_HEIGHT: int = 1920
    VIDEO_FPS: int = 30
    X264_PRESET: str = "veryfast"
    X264_CRF: int = 21
    FFMPEG_THREADS: int = 0          # 0 = let FFmpeg decide
    SCENE_RENDER_PARALLELISM: int = 2
    ENABLE_MUSIC: bool = True
    MUSIC_VOLUME: float = 0.16

    # ── Job queue / workers ────────────────────────────────────────────────
    EMBEDDED_WORKER: bool = True      # run workers inside the API process
    # Workers only claim jobs from this queue. Give each developer their own value when
    # several machines share one MongoDB, so nobody's laptop picks up someone else's jobs.
    JOB_QUEUE: str = "qreate"
    WORKER_CONCURRENCY: int = 1       # videos rendered at once per process
    JOB_LEASE_SECONDS: int = 180
    JOB_MAX_ATTEMPTS: int = 2
    MAX_QUEUE_DEPTH: int = 200        # reject new jobs above this (HTTP 429)
    MAX_BATCH_SIZE: int = 25

    # ── Authentication & Security ──────────────────────────────────────────
    JWT_SECRET_KEY: str = "qreate-jwt-secret-key-super-secure-token-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins(self) -> List[str]:
        origins = [self.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"]
        origins += [o.strip() for o in self.EXTRA_CORS_ORIGINS.split(",") if o.strip()]
        return [o.rstrip("/") for o in origins if o]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
