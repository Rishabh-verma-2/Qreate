"""Video generation (queued), task polling, and retrieval routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.database import crud
from app.schemas.schemas import VideoGenerateRequest
from app.worker import queue

router = APIRouter(prefix="/api/videos", tags=["Videos"])
logger = logging.getLogger(__name__)


async def ensure_capacity(new_jobs: int = 1) -> None:
    """Back-pressure: refuse work when the queue is already deep (HTTP 429)."""
    depth = await queue.queue_depth()
    limit = get_settings().MAX_QUEUE_DEPTH
    if depth + new_jobs > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Render queue is full ({depth} jobs waiting). Please try again in a few minutes.",
        )


@router.post("/generate", response_model=dict, status_code=202)
async def generate_video(body: VideoGenerateRequest):
    """Queue a render for an existing (edited) script. Poll /api/videos/tasks/{id}."""
    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    script = await crud.get_script(body.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.get("scenes"):
        raise HTTPException(status_code=422, detail="Script has no scenes to render")

    # Idempotency: one active render per script
    for t in await crud.list_tasks_for_project(body.project_id):
        if t.get("script_id") == body.script_id and t.get("status") in queue.ACTIVE_STATUSES:
            return {"data": t, "message": "A video task for this script is already in progress"}

    await ensure_capacity()
    task = await queue.enqueue({
        "project_id": body.project_id,
        "script_id": body.script_id,
        "generation_settings": {"aspect_ratio": "9:16", "resolution": "1080x1920", "engine": "stock-footage"},
    })
    logger.info(f"Video job queued: {task['id']}")
    return {"data": task, "message": "Video generation queued"}


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task_status(task_id: str):
    """Get video generation task status."""
    task = await crud.get_video_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return {"data": task}


@router.get("", response_model=dict)
async def list_videos():
    """List all generated videos."""
    videos = await crud.list_generated_videos(limit=100)
    return {"data": videos, "total": len(videos)}


@router.get("/{video_id}", response_model=dict)
async def get_video(video_id: str):
    """Get a generated video by ID."""
    video = await crud.get_generated_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
    return {"data": video}
