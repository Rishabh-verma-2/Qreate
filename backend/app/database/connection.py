"""MongoDB database connection and helpers."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    global _client, _db
    settings = get_settings()
    if not settings.MONGODB_URI:
        logger.warning("MONGODB_URI not set — running without database persistence")
        return
    try:
        _client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000, maxPoolSize=50)
        # Verify connection
        await _client.admin.command("ping")
        _db = _client[settings.MONGODB_DATABASE]
        logger.info(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")
        await _ensure_indexes()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        _client = None
        _db = None


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    return _db


async def _ensure_indexes() -> None:
    if _db is None:
        return
    try:
        # Projects
        await _db.projects.create_index([("created_at", DESCENDING)])
        await _db.projects.create_index([("status", ASCENDING)])

        # Scripts
        await _db.scripts.create_index([("project_id", ASCENDING)])
        await _db.scripts.create_index([("created_at", DESCENDING)])

        # Video tasks
        await _db.video_tasks.create_index([("project_id", ASCENDING)])
        await _db.video_tasks.create_index([("script_id", ASCENDING)])
        await _db.video_tasks.create_index([("agnes_video_id", ASCENDING)])
        await _db.video_tasks.create_index([("status", ASCENDING)])
        await _db.video_tasks.create_index([("created_at", DESCENDING)])
        # Queue claim: oldest queued job first
        await _db.video_tasks.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
        await _db.video_tasks.create_index([("batch_id", ASCENDING)])

        # Batches
        await _db.batches.create_index([("created_at", DESCENDING)])

        # Generated videos
        await _db.generated_videos.create_index([("project_id", ASCENDING)])
        await _db.generated_videos.create_index([("task_id", ASCENDING)])
        await _db.generated_videos.create_index([("created_at", DESCENDING)])
        await _db.generated_videos.create_index([("batch_id", ASCENDING)])

        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")
