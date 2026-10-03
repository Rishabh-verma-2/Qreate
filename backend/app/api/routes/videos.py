"""Video generation, task polling, and retrieval routes."""

import asyncio
import logging
from datetime import datetime, timezone

import os
import tempfile
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.config import get_settings
from app.core.errors import AgnesAPIError, AgnesQueueFullError
from app.database import crud
from app.schemas.schemas import VideoGenerateRequest
from app.services.agnes.client import get_agnes_client
from app.services.cloudinary.uploader import upload_video_file, upload_video_from_url
from app.services.script.generator import script_to_video_prompt
from app.services.purffle import (
    PurffleRenderResult,
    qreate_script_to_purffle,
    run_purffle_render,
    validate_purffle_mp4,
    source_visuals_for_scenes,
)
from app.services.video_engine import generate_free_video, sync_audio_and_captions_to_video

router = APIRouter(prefix="/api/videos", tags=["Videos"])
logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


@router.post("/generate", response_model=dict, status_code=202)
async def generate_video(body: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """Submit a video generation task.

    Returns immediately with a task ID. Poll /api/videos/tasks/{task_id} for status.
    Prevents duplicate submissions for the same script.
    """
    # Validate project and script
    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script = await crud.get_script(body.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Prevent duplicate in-progress task for same script
    existing_tasks = await crud.list_tasks_for_project(body.project_id)
    for t in existing_tasks:
        if (
            t.get("script_id") == body.script_id
            and t.get("status") in ("pending", "queued", "in_progress")
        ):
            return {
                "data": t,
                "message": "A video task for this script is already in progress",
            }

    # Build video prompt from script
    prompt = script_to_video_prompt(script)
    if not prompt:
        raise HTTPException(status_code=422, detail="Script has no content to generate video from")

    settings = get_settings()
    generation_settings = {
        "model": settings.AGNES_VIDEO_MODEL,
        "mode": body.mode,
        "duration_seconds": body.duration_seconds,
        "aspect_ratio": body.aspect_ratio,
        "seed": body.seed,
        "engine": body.engine,
        "prompt_preview": prompt[:200],
    }

    # Create task record in DB
    task = await crud.create_video_task({
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
    logger.info(f"Video task created: {task_id}")

    # Submit to Agnes or Free Engine in background
    background_tasks.add_task(
        _run_video_generation,
        task_id=task_id,
        project_id=body.project_id,
        prompt=prompt,
        mode=body.mode,
        seconds=str(body.duration_seconds),
        aspect_ratio=body.aspect_ratio,
        seed=body.seed,
        script_id=body.script_id,
        engine=body.engine,
    )

    return {"data": task, "message": "Video generation started"}


async def _generate_via_free_engine(task_id: str, project_id: str, script_id: str, update_fn) -> bool:
    """Render video using the Free AI Multi-Scene Video Synthesis Engine."""
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
    logger.info(f"[Task {task_id}] Free video synthesis completed! Video: {cloudinary_url}")
    return True


async def _generate_via_purffle_engine(
    task_id: str,
    project_id: str,
    script_id: str,
    aspect_ratio: str,
    update_fn,
) -> bool:
    """Render video using the verified PurffleShorts rendering pipeline."""
    # Step 4 task progress: in_progress 15%
    await update_fn(status="in_progress", progress=15)

    script = await crud.get_script(script_id)
    if not script:
        raise ValueError(f"Script not found for video generation: {script_id}")

    # script/adapter 25%
    await update_fn(progress=25)

    # Visual sourcing: download and format high-res 1080x1920 visuals for each scene
    scenes = script.get("scenes") or []
    topic = str(script.get("original_prompt") or script.get("title") or "Science explainer")
    media_dir = os.path.join(tempfile.gettempdir(), f"purffle_media_{task_id}")

    search_queries = None
    try:
        sourced = await source_visuals_for_scenes(scenes, topic, media_dir)
        search_queries = [kw for kw, _ in sourced]
        logger.info(f"[Task {task_id}] Sourced {len(sourced)} scene visuals into {media_dir}")
    except Exception as v_err:
        logger.warning(f"[Task {task_id}] Visual sourcing error: {v_err}. Continuing with fallback visuals.")

    purffle_data = qreate_script_to_purffle(script, topic=topic, scene_search_queries=search_queries)

    # Purffle rendering 50-85%
    await update_fn(progress=50)

    loop = asyncio.get_running_loop()

    def _sync_progress_cb(pct: int, msg: str):
        # Map internal 0..100% to task progress 50..85%
        mapped = min(85, max(50, 50 + int(pct * 0.35)))
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(update_fn(progress=mapped))
        )

    aspect = "9:16"
    if aspect_ratio in ("9:16", "16:9", "1:1", "4:5"):
        aspect = aspect_ratio

    result: PurffleRenderResult = await asyncio.to_thread(
        run_purffle_render,
        purffle_script_data=purffle_data,
        aspect_ratio=aspect,
        timeout_seconds=420,
        progress_callback=_sync_progress_cb,
        media_dir=media_dir,
    )

    if not result.ok or not result.mp4_path:
        raise RuntimeError(result.error_message or "Purffle video rendering failed")

    # output validation 90%
    await update_fn(progress=90)
    validation = validate_purffle_mp4(result.mp4_path, expected_aspect=aspect)
    if not validation.is_valid:
        raise ValueError(f"Generated video failed validation: {validation.error}")

    # Cloudinary upload (safe fallback if unavailable)
    cloudinary_url = None
    cloudinary_public_id = None
    try:
        cloudinary_url, cloudinary_public_id = await upload_video_file(
            file_path=result.mp4_path,
            project_id=project_id,
            task_id=task_id,
        )
    except Exception as c_err:
        logger.warning(
            f"[Task {task_id}] Cloudinary upload skipped or unconfigured ({c_err}). Retaining local video artifact."
        )

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

    # completed 100%
    await update_fn(
        status="completed",
        progress=100,
        completed_at=_utcnow(),
        generated_video_id=gen_video["id"],
        cloudinary_url=cloudinary_url,
    )
    logger.info(f"[Task {task_id}] Purffle video generation completed! MP4: {result.mp4_path}")
    return True


async def _run_video_generation(
    task_id: str,
    project_id: str,
    prompt: str,
    mode: str,
    seconds: str,
    aspect_ratio: str,
    seed,
    script_id: str,
    engine: str = "auto",
):
    """Background task: submit to Agnes, poll, or use free video synthesis engine."""
    settings = get_settings()
    client = get_agnes_client()

    async def _update_task(**kwargs):
        await crud.update_video_task(task_id, kwargs)

    # If requested purffle engine directly, run it immediately
    if engine == "purffle":
        try:
            await _generate_via_purffle_engine(task_id, project_id, script_id, aspect_ratio, _update_task)
            return
        except Exception as e:
            logger.exception(f"[Task {task_id}] Purffle engine error")
            await _update_task(status="failed", error_message=str(e), completed_at=_utcnow())
            return

    # If requested free engine directly, run it immediately
    if engine == "free":
        try:
            await _generate_via_free_engine(task_id, project_id, script_id, _update_task)
            return
        except Exception as e:
            logger.exception(f"[Task {task_id}] Free engine error")
            await _update_task(status="failed", error_message=str(e), completed_at=_utcnow())
            return

    try:
        # Submit to Agnes
        await _update_task(status="queued")
        agnes_response = await client.create_video_task(
            prompt=prompt,
            mode=mode,
            seconds=seconds,
            aspect_ratio=aspect_ratio,
            seed=seed,
        )
        agnes_video_id = agnes_response.get("_polling_video_id")
        await _update_task(status="in_progress", agnes_video_id=agnes_video_id, progress=5)
        logger.info(f"[Task {task_id}] Agnes video submitted: agnes_video_id={agnes_video_id}")

        # Poll for completion
        poll_count = 0
        max_attempts = settings.VIDEO_POLL_MAX_ATTEMPTS
        while poll_count < max_attempts:
            await asyncio.sleep(settings.VIDEO_POLL_INTERVAL_SECONDS)
            poll_count += 1

            status_data = await client.get_video_status(agnes_video_id)
            agnes_status = status_data.get("status", "")
            progress = status_data.get("progress", 0)

            logger.debug(f"[Task {task_id}] Poll #{poll_count}: status={agnes_status} progress={progress}")
            await _update_task(status="in_progress", progress=min(int(progress), 99))

            if agnes_status == "completed":
                video_url = status_data.get("url")
                if not video_url:
                    raise AgnesAPIError("Agnes returned completed but no URL", status_code=502)

                # Process raw Agnes video: add neural voiceover and synchronized captions
                script = await crud.get_script(script_id)
                cloudinary_url, cloudinary_public_id = await sync_audio_and_captions_to_video(
                    video_url=video_url,
                    script=script or {},
                    task_id=task_id,
                    project_id=project_id,
                )

                # Save to generated_videos collection
                gen_video = await crud.create_generated_video({
                    "project_id": project_id,
                    "script_id": script_id,
                    "task_id": task_id,
                    "cloudinary_url": cloudinary_url,
                    "cloudinary_public_id": cloudinary_public_id,
                    "original_url": video_url,
                    "file_format": "mp4",
                    "duration_seconds": int(status_data.get("seconds", 0) or 5),
                })

                await _update_task(
                    status="completed",
                    progress=100,
                    completed_at=_utcnow(),
                    generated_video_id=gen_video["id"],
                    cloudinary_url=cloudinary_url,
                )
                logger.info(f"[Task {task_id}] Completed! Video: {cloudinary_url}")
                return

            elif agnes_status == "failed":
                err_msg = status_data.get("error_message", "Video generation failed")
                raise AgnesAPIError(f"Video generation failed: {err_msg}", status_code=502)

        # Timed out
        raise AgnesAPIError("Video generation timed out after maximum wait time", status_code=504)

    except (AgnesAPIError, AgnesQueueFullError) as e:
        logger.warning(f"[Task {task_id}] Agnes unavailable or rate-limited ({e}). Falling back to Free AI Multi-Scene Video Synthesis Engine.")
        try:
            await _generate_via_free_engine(task_id, project_id, script_id, _update_task)
            return
        except Exception as fallback_err:
            logger.exception(f"[Task {task_id}] Fallback generator error: {fallback_err}")
            await _update_task(
                status="failed",
                error_message=f"Generation error: {str(fallback_err)}",
                completed_at=_utcnow(),
            )
    except Exception as e:
        logger.exception(f"[Task {task_id}] Unexpected error")
        await _update_task(
            status="failed",
            error_message=f"Unexpected error: {str(e)[:200]}",
            completed_at=_utcnow(),
        )


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
