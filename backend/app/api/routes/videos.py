import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone

from typing import Any, Dict, Optional, Union
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx

from app.core.config import get_settings
from app.database import crud
from app.schemas.schemas import VideoGenerateRequest, WanGenerateRequest, SceneRegenerateRequest
from app.services.cloudinary.uploader import upload_video_file
from app.services.script.generator import script_to_video_prompt
from app.services.purffle import (
    PurffleRenderResult,
    qreate_script_to_purffle,
    run_purffle_render,
    source_visuals_for_scenes,
    validate_purffle_mp4,
)
from app.services.video_engine import generate_free_video, sync_audio_and_captions_to_video
from app.core.ratelimit import enforce
from app.worker import queue

router = APIRouter(prefix="/api/videos", tags=["Videos"])
logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


async def ensure_capacity(new_jobs: int = 1) -> None:
    """Back-pressure for the queued pipeline: refuse work when the queue is deep (HTTP 429)."""
    depth = await queue.queue_depth()
    limit = get_settings().MAX_QUEUE_DEPTH
    if depth + new_jobs > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Render queue is full ({depth} jobs waiting). Please try again in a few minutes.",
        )


@router.post("/generate", response_model=dict, status_code=202)
async def generate_video(
    body: Union[WanGenerateRequest, VideoGenerateRequest],
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Submit a video generation task.

    Returns immediately with a task ID. Poll /api/videos/tasks/{task_id} or
    /api/videos/{video_id}/status for status.
    """
    # Project handling: if project_id is missing or doesn't exist, create a standalone project for this custom video
    project_id = getattr(body, "project_id", None)
    project = None
    if project_id and project_id not in ("default", "custom", "none", ""):
        project = await crud.get_project(project_id)

    if not project:
        title = (getattr(body, "prompt", None) or getattr(body, "topic", None) or "Custom AI Video")[:60]
        project = await crud.create_project({
            "name": title,
            "description": "Standalone custom AI video",
        })
        project_id = project["id"]
        if hasattr(body, "project_id"):
            body.project_id = project_id

    script = None
    script_id = getattr(body, "script_id", None)
    if script_id:
        script = await crud.get_script(script_id)
        if not script and getattr(body, "engine", "") != "wan":
            raise HTTPException(status_code=404, detail="Script not found")

    # Prevent duplicate in-progress task for same script
    if script_id:
        existing_tasks = await crud.list_tasks_for_project(project_id)
        for t in existing_tasks:
            if (
                t.get("script_id") == script_id
                and t.get("status") in ("pending", "queued", "in_progress")
            ):
                return {
                    "data": t,
                    "message": "A video task for this script is already in progress",
                }

    # For Wan AI Director, bypass rate limiting; otherwise enforce configured limit
    if getattr(body, "engine", "") == "wan":
        owner = "local:ai_director"
    else:
        owner = await enforce(request, "video")

    # AI Video Director (Wan2.1 / ComfyUI / Native fallback)
    if getattr(body, "engine", "") == "wan":
        await ensure_capacity()
        prompt_val = getattr(body, "prompt", None)
        if not prompt_val and script:
            prompt_val = script_to_video_prompt(script)
        if not prompt_val:
            prompt_val = "Cinematic scene"

        duration_val = getattr(body, "duration", None) or getattr(body, "duration_seconds", 30)
        task = await queue.enqueue({
            "owner": owner,
            "project_id": body.project_id,
            "script_id": script_id,
            "generation_settings": {
                "aspect_ratio": getattr(body, "aspect_ratio", "16:9"),
                "engine": "wan",
                "duration": duration_val,
                "prompt": prompt_val,
                "style": getattr(body, "style", "cinematic 3D animation"),
                "wan_mode": getattr(body, "wan_mode", "t2v"),
                "quality": getattr(body, "quality", "development"),
                "plan_id": getattr(body, "plan_id", None),
            },
        })
        logger.info(f"Wan2.1 AI Director job queued: {task['id']}")
        return {"data": task, "message": "AI Director video generation queued"}

    # Qreate reel pipeline: queued, rendered by the worker pool (scales across processes)
    if body.engine == "qreate":
        if not script or not script.get("scenes"):
            raise HTTPException(status_code=422, detail="Script has no scenes to render")
        await ensure_capacity()
        task = await queue.enqueue({
            "owner": owner,
            "project_id": body.project_id,
            "script_id": body.script_id,
            "generation_settings": {"aspect_ratio": "9:16", "resolution": "1080x1920", "engine": "qreate"},
        })
        logger.info(f"Qreate pipeline job queued: {task['id']}")
        return {"data": task, "message": "Video generation queued"}


    # Build video prompt from script (PurffleShorts / free / Agnes engines)
    prompt = script_to_video_prompt(script)
    if not prompt:
        raise HTTPException(status_code=422, detail="Script has no content to generate video from")

    generation_settings = {
        "mode": body.mode,
        "duration_seconds": body.duration_seconds,
        "aspect_ratio": body.aspect_ratio,
        "seed": body.seed,
        "engine": "purffle",
        "prompt_preview": prompt[:200],
    }

    # Create task record in DB
    task = await crud.create_video_task({
        "owner": owner,
        "project_id": body.project_id,
        "script_id": body.script_id,
        "agnes_video_id": None,
        "status": "pending",
        "progress": 0,
        "error_message": None,
        "generation_settings": generation_settings,
        "completed_at": None,
    })

    task_id = task["id"]
    logger.info(f"[PurffleV3] Video task created: {task_id}")

    # Submit PurffleShorts V3 render in background
    background_tasks.add_task(
        _run_video_generation,
        task_id=task_id,
        project_id=body.project_id,
        script_id=body.script_id,
        aspect_ratio=body.aspect_ratio,
    )

    return {"data": task, "message": "Video generation started"}



async def _generate_via_native_engine(
    task_id: str,
    project_id: str,
    script_id: str,
    update_fn,
    aspect_ratio: str = "9:16",
) -> bool:
    """Render video using the built-in native animated motion graphics engine (Pillow + FFmpeg)."""
    await update_fn(status="in_progress", progress=15)
    script = await crud.get_script(script_id)
    if not script:
        raise ValueError("Script not found for video generation")

    async def _progress_cb(pct: int, msg: str):
        await update_fn(progress=pct)

    cloudinary_url, cloudinary_public_id, duration_sec = await generate_free_video(
        task_id=task_id,
        project_id=project_id,
        script=script,
        progress_callback=_progress_cb,
        aspect_ratio=aspect_ratio,
    )

    gen_video = await crud.create_generated_video({
        "project_id": project_id,
        "script_id": script_id,
        "task_id": task_id,
        "cloudinary_url": cloudinary_url,
        "cloudinary_public_id": cloudinary_public_id,
        "original_url": cloudinary_url,
        "file_format": "mp4",
        "duration_seconds": duration_sec,
    })

    await update_fn(
        status="completed",
        progress=100,
        completed_at=_utcnow(),
        generated_video_id=gen_video["id"],
        cloudinary_url=cloudinary_url,
    )
    logger.info(f"[Task {task_id}] Native animated video completed: {cloudinary_url}")
    return True


async def _generate_via_purffle_engine(
    task_id: str,
    project_id: str,
    script_id: str,
    aspect_ratio: str,
    update_fn,
) -> bool:
    """Render video using the PurffleShorts animated motion graphics pipeline."""
    aspect = "9:16"
    if aspect_ratio in ("9:16", "16:9", "1:1", "4:5"):
        aspect = aspect_ratio

    # If external purffle CLI is not explicitly installed/configured,
    # render directly via our native Purffle procedural animation engine
    from app.services.purffle.runner import _find_purffle_python_on_system
    has_external_cli = bool(os.environ.get("PURFFLE_PYTHON_EXE") or _find_purffle_python_on_system())

    if not has_external_cli:
        logger.info(f"[Task {task_id}] Using native Purffle animated motion graphics engine.")
        return await _generate_via_native_engine(task_id, project_id, script_id, update_fn, aspect_ratio=aspect)

    await update_fn(status="in_progress", progress=15)

    script = await crud.get_script(script_id)
    if not script:
        raise ValueError(f"Script not found for video generation: {script_id}")

    await update_fn(progress=25)

    # Visual sourcing for external CLI
    scenes = script.get("scenes") or []
    topic = str(script.get("original_prompt") or script.get("title") or "Science explainer")
    media_dir = os.path.join(tempfile.gettempdir(), f"purffle_media_{task_id}")

    search_queries = None
    try:
        sourced = await source_visuals_for_scenes(scenes, topic, media_dir)
        search_queries = [kw for kw, _ in sourced]
        logger.info(f"[Task {task_id}] Sourced {len(sourced)} scene visuals into {media_dir}")
    except Exception as v_err:
        logger.warning(f"[Task {task_id}] Visual sourcing notice: {v_err}. Continuing with fallback visuals.")

    purffle_data = qreate_script_to_purffle(script, topic=topic, scene_search_queries=search_queries)

    await update_fn(progress=50)

    loop = asyncio.get_running_loop()

    def _sync_progress_cb(pct: int, msg: str):
        mapped = min(85, max(50, 50 + int(pct * 0.35)))
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(update_fn(progress=mapped))
        )

    result: Optional[PurffleRenderResult] = None
    try:
        result = await asyncio.to_thread(
            run_purffle_render,
            purffle_script_data=purffle_data,
            aspect_ratio=aspect,
            timeout_seconds=420,
            progress_callback=_sync_progress_cb,
            media_dir=media_dir,
        )
    except Exception as run_err:
        logger.warning(f"[Task {task_id}] Purffle CLI runner: {run_err}. Using native animated engine.")

    # If Purffle CLI is unavailable or failed, fall back to the native motion graphics engine
    if not result or not result.ok or not result.mp4_path:
        logger.info(f"[Task {task_id}] purffle_shorts CLI not available — rendering via native animated engine.")
        return await _generate_via_native_engine(task_id, project_id, script_id, update_fn, aspect_ratio=aspect)

    await update_fn(progress=90)
    validation = validate_purffle_mp4(result.mp4_path, expected_aspect=aspect)

    cloudinary_url = None
    cloudinary_public_id = None
    try:
        cloudinary_url, cloudinary_public_id = await upload_video_file(
            file_path=result.mp4_path,
            project_id=project_id,
            task_id=task_id,
        )
    except Exception as c_err:
        logger.warning(f"[Task {task_id}] Cloudinary upload skipped ({c_err}). Retaining local video artifact.")

    duration_sec = int(round(validation.duration_seconds or result.duration_seconds or 30))
    video_url = cloudinary_url or f"file:///{result.mp4_path.replace(os.sep, '/')}"

    gen_video = await crud.create_generated_video({
        "project_id": project_id,
        "script_id": script_id,
        "task_id": task_id,
        "cloudinary_url": cloudinary_url,
        "cloudinary_public_id": cloudinary_public_id,
        "original_url": video_url,
        "file_format": "mp4",
        "duration_seconds": duration_sec,
    })

    await update_fn(
        status="completed",
        progress=100,
        completed_at=_utcnow(),
        generated_video_id=gen_video["id"],
        cloudinary_url=cloudinary_url,
    )
    logger.info(f"[Task {task_id}] Purffle video synthesis completed! Video: {cloudinary_url or video_url}")
    return True


async def _run_video_generation(
    task_id: str,
    project_id: str,
    script_id: str,
    aspect_ratio: str,
):
    """Background task: render professional animated video via PurffleShorts V3."""

    async def _update_task(**kwargs):
        await crud.update_video_task(task_id, kwargs)

    try:
        await _generate_via_purffle_engine(task_id, project_id, script_id, aspect_ratio, _update_task)
    except Exception as e:
        logger.exception(f"[Task {task_id}] PurffleShorts V3 render error")
        await _update_task(
            status="failed",
            error_message=str(e)[:500],
            completed_at=_utcnow(),
        )


@router.get("/tasks", response_model=dict)
async def list_tasks(active: bool = False, limit: int = 20):
    """Recent render tasks (active=true → only queued/in-progress), newest first."""
    tasks = await crud.list_recent_tasks(limit=min(max(limit, 1), 100), active_only=active)
    return {"data": tasks}


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


@router.get("/download")
async def download_video(url: str, filename: Optional[str] = "qreate_video.mp4"):
    """Proxy streaming download for video URLs with Content-Disposition attachment header."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    clean_filename = filename if filename.endswith(".mp4") else f"{filename}.mp4"

    async def stream_video():
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail="Failed to fetch video stream")
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(
        stream_video(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/{video_id}/status", response_model=dict)
async def get_video_status(video_id: str):
    """Get video task progress and status details."""
    task = await crud.get_video_task(video_id)
    if not task:
        gen = await crud.get_generated_video(video_id)
        if gen and gen.get("task_id"):
            task = await crud.get_video_task(gen["task_id"])
    if not task:
        raise HTTPException(status_code=404, detail=f"Video task not found: {video_id}")
    return {
        "data": {
            "id": task.get("id"),
            "status": task.get("status"),
            "progress": task.get("progress", 0),
            "stage": task.get("stage"),
            "current_scene": task.get("current_scene"),
            "total_scenes": task.get("total_scenes"),
            "error_message": task.get("error_message"),
            "cloudinary_url": task.get("cloudinary_url"),
            "thumbnail_url": task.get("thumbnail_url"),
            "completed_at": task.get("completed_at"),
            "generation_settings": task.get("generation_settings", {}),
        }
    }


@router.post("/{video_id}/scenes/{scene_id}/regenerate", response_model=dict, status_code=202)
async def regenerate_scene(
    video_id: str,
    scene_id: str,
    body: SceneRegenerateRequest,
):
    """Regenerate visual and motion instructions for a single scene in a video plan."""
    from app.services.llm.video_director import QwenVideoDirector

    task = await crud.get_video_task(video_id)
    plan_id = None
    if task:
        plan_id = task.get("video_plan_id") or task.get("generation_settings", {}).get("plan_id")
    if not plan_id:
        plan_doc = await crud.get_plan_by_task(video_id)
        if plan_doc:
            plan_id = plan_doc.get("id")

    if not plan_id:
        # Check if video_id is plan_id directly
        plan_doc = await crud.get_video_plan(video_id)
        if plan_doc:
            plan_id = video_id
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Video plan not found for video/task: {video_id}",
            )
    else:
        plan_doc = await crud.get_video_plan(plan_id)

    if not plan_doc:
        raise HTTPException(status_code=404, detail="Video plan document not found")

    scenes = plan_doc.get("scenes", [])
    target_scene = next((s for s in scenes if s.get("id") == scene_id), None)
    if not target_scene:
        raise HTTPException(
            status_code=404,
            detail=f"Scene '{scene_id}' not found in video plan",
        )

    director = QwenVideoDirector()
    try:
        updated_scene = await director.regenerate_scene(
            original_scene=target_scene,
            instruction=body.instruction,
            video_style=plan_doc.get("style", "cinematic"),
        )
        await crud.update_plan_scene(plan_id, scene_id, updated_scene.model_dump())
        return {
            "status": "regenerated",
            "scene_id": scene_id,
            "message": "Scene instructions regenerated successfully",
            "scene": updated_scene.model_dump(),
        }
    except Exception as e:
        logger.error(f"Scene regeneration error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to regenerate scene: {str(e)}",
        )


@router.get("/{video_id}", response_model=dict)
async def get_video(video_id: str):
    """Get a generated video by ID."""
    video = await crud.get_generated_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
    return {"data": video}

