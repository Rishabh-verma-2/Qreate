"""Cloudinary upload service."""

import asyncio
import logging
import os
from typing import Optional, Tuple

import cloudinary
import cloudinary.uploader

from app.core.config import get_settings
from app.core.errors import CloudinaryError

logger = logging.getLogger(__name__)

_configured = False


def _configure():
    global _configured
    if _configured:
        return
    settings = get_settings()
    if not all([settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET]):
        logger.warning("Cloudinary credentials not set — upload will be skipped")
        return
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    _configured = True
    logger.info("Cloudinary configured")


def is_cloudinary_configured() -> bool:
    _configure()
    return _configured


async def upload_video_from_url(
    video_url: str,
    project_id: str,
    task_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Download a video URL and upload it to Cloudinary.

    Returns (cloudinary_url, cloudinary_public_id) or (None, None) if disabled.
    """
    _configure()
    if not _configured:
        logger.warning("Cloudinary not configured — returning original URL")
        return video_url, None

    folder = f"qreate/projects/{project_id}"
    public_id = f"{folder}/video_{task_id}"

    try:
        logger.info(f"Uploading video to Cloudinary: {video_url[:60]}...")
        result = cloudinary.uploader.upload(
            video_url,
            resource_type="video",
            public_id=public_id,
            overwrite=True,
            invalidate=True,
        )
        secure_url = result.get("secure_url")
        public_id_out = result.get("public_id")
        logger.info(f"Cloudinary upload success: {secure_url}")
        return secure_url, public_id_out
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        # Don't raise — fall back to original URL
        return video_url, None


async def upload_video_file(
    file_path: str,
    project_id: str,
    task_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Upload a local video file to Cloudinary."""
    _configure()
    if not _configured:
        raise CloudinaryError("Cloudinary is not configured (set CLOUDINARY_* env vars)")

    folder = f"qreate/projects/{project_id}"
    public_id = f"{folder}/video_{task_id}"

    try:
        logger.info(f"Uploading local file {file_path} to Cloudinary...")
        # The SDK is synchronous — run it in a thread so the event loop keeps serving requests
        result = await asyncio.to_thread(
            cloudinary.uploader.upload_large if os.path.getsize(file_path) > 20_000_000 else cloudinary.uploader.upload,
            file_path,
            resource_type="video",
            public_id=public_id,
            overwrite=True,
            invalidate=True,
        )
        secure_url = result.get("secure_url")
        public_id_out = result.get("public_id")
        logger.info(f"Cloudinary upload success: {secure_url}")
        return secure_url, public_id_out
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise CloudinaryError(str(e))



async def delete_video(public_id: str) -> bool:
    """Delete a video from Cloudinary by public_id."""
    _configure()
    if not _configured or not public_id:
        return False
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="video")
        return result.get("result") == "ok"
    except Exception as e:
        logger.error(f"Cloudinary delete failed for {public_id}: {e}")
        return False
