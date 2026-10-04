"""Creator media uploads — their own photos/clips become the video's visuals."""

import asyncio
import logging
import os
import tempfile
import uuid
from typing import List

import cloudinary.uploader
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.cloudinary.uploader import is_cloudinary_configured

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])
logger = logging.getLogger(__name__)

MAX_FILES = 15
MAX_BYTES = 60 * 1024 * 1024


async def _store(upload: UploadFile) -> dict:
    ctype = (upload.content_type or "").lower()
    if not (ctype.startswith("image/") or ctype.startswith("video/")):
        raise HTTPException(status_code=415, detail=f"{upload.filename}: only images and videos are supported")
    kind = "video" if ctype.startswith("video/") else "image"

    suffix = os.path.splitext(upload.filename or "")[1] or (".mp4" if kind == "video" else ".jpg")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        size = 0
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                os.unlink(tmp.name)
                raise HTTPException(status_code=413, detail=f"{upload.filename}: file is larger than 60 MB")
            tmp.write(chunk)
    try:
        result = await asyncio.to_thread(
            cloudinary.uploader.upload, tmp.name,
            resource_type=kind, folder="qreate/uploads", public_id=uuid.uuid4().hex,
        )
    finally:
        os.unlink(tmp.name)
    return {
        "url": result["secure_url"],
        "kind": kind,
        "width": result.get("width"),
        "height": result.get("height"),
        "duration": result.get("duration"),
        "name": upload.filename,
    }


@router.post("", response_model=dict, status_code=201)
async def upload_media(files: List[UploadFile] = File(...)):
    """Upload up to 15 photos/videos. Returns hosted URLs to pass as `user_media`."""
    if not is_cloudinary_configured():
        raise HTTPException(status_code=503, detail="Uploads need Cloudinary to be configured")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail=f"Upload at most {MAX_FILES} files at once")
    items = await asyncio.gather(*(_store(f) for f in files))
    return {"data": items}
