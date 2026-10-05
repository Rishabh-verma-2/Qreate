"""Wan2.1 AI Video Director pipeline runner.

Orchestrates the complete end-to-end pipeline:
  1. Parse/validate video plan (from Qwen3)
  2. Resolve character reference images
  3. Generate each scene via Wan2.1 (or native engine as fallback)
  4. Generate TTS narration per scene
  5. Compose: scenes + audio + transitions → final MP4
  6. Upload to Cloudinary (or return local path if Cloudinary not configured)

This module follows the same patterns as services/pipeline/runner.py
but is specific to the AI Director / Wan2.1 pipeline.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.config import get_settings
from app.core.errors import WanError, CloudinaryError
from app.database import crud
from app.services.characters.service import CharacterService
from app.services.cloudinary.uploader import upload_video_file, is_cloudinary_configured
from app.services.llm.schemas import Scene, VideoPlan
from app.services.media.tts import pick_voice, synthesize
from app.services.media.ffmpeg import probe_duration, run_ffmpeg
from app.services.video import get_video_engine
from app.services.wan_pipeline.ffmpeg_composer import wan_compose

logger = logging.getLogger(__name__)

Reporter = Callable[[int, str], Awaitable[None]]


async def produce_wan_video(
    video_plan: VideoPlan,
    job_id: str,
    project_id: str,
    report: Reporter,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full AI Director pipeline from VideoPlan to final uploaded MP4.

    Args:
        video_plan: Validated VideoPlan from Qwen3.
        job_id: Job/task identifier (for logging and temp file naming).
        project_id: MongoDB project_id (for Cloudinary folder structure).
        report: Async progress callback `(progress_int, stage_str)`.
        task_id: DB task_id for progress updates (may equal job_id).

    Returns:
        Dict with keys: cloudinary_url, thumbnail_url, duration_seconds,
        file_size_mb, shots, timings.

    Raises:
        WanError: If scene generation fails for all scenes.
    """
    s = get_settings()
    timings: Dict[str, float] = {}
    t0 = time.monotonic()

    total_scenes = len(video_plan.scenes)
    engine = get_video_engine()

    with tempfile.TemporaryDirectory(prefix=f"wan_{job_id}_") as work_dir:

        # ── Stage 1: Character reference images ──────────────────────────────
        await report(10, "Generating character references...")
        char_service = CharacterService(job_id, work_dir)
        await char_service.resolve_all(video_plan)
        timings["characters"] = time.monotonic() - t0

        # ── Stage 2: Per-scene video generation ──────────────────────────────
        scene_clips: List[str] = []
        scene_audio: List[str] = []
        scene_durations: List[float] = []

        for i, scene in enumerate(video_plan.scenes):
            scene_pct = int(15 + 55 * (i / total_scenes))
            await report(scene_pct, f"Generating scene {i + 1}/{total_scenes}...")

            # Update DB with current scene info
            if task_id:
                try:
                    await crud.update_video_task(task_id, {
                        "current_scene": i + 1,
                        "total_scenes": total_scenes,
                        "stage": f"Generating scene {i + 1}/{total_scenes}",
                        "progress": scene_pct,
                    })
                except Exception:
                    pass

            clip_path = await _generate_scene_with_retry(
                engine=engine,
                scene=scene,
                video_plan=video_plan,
                work_dir=work_dir,
                index=i,
                max_attempts=s.WAN_SCENE_MAX_ATTEMPTS,
            )
            scene_clips.append(clip_path)
            actual_duration = await probe_duration(clip_path)
            scene_durations.append(actual_duration or float(scene.duration))

        timings["scenes"] = time.monotonic() - t0

        # ── Stage 3: TTS narration per scene ─────────────────────────────────
        await report(70, "Generating narration...")
        voice = video_plan.audio.tts_voice or pick_voice(
            video_plan.language, "cinematic", "male"
        )
        for i, scene in enumerate(video_plan.scenes):
            if not scene.narration.strip():
                scene_audio.append("")
                continue
            audio_path = os.path.join(work_dir, f"narration_{i:03d}.mp3")
            try:
                narration = await synthesize(
                    text=scene.narration,
                    audio_path=audio_path,
                    voice=voice,
                    rate="+5%",
                    pitch="+0Hz",
                )
                scene_audio.append(narration.audio_path)
            except Exception as e:
                logger.warning(f"TTS failed for scene {i + 1}: {e}. Continuing without narration.")
                scene_audio.append("")

        timings["tts"] = time.monotonic() - t0

        # ── Stage 4: FFmpeg composition ───────────────────────────────────────
        await report(80, "Composing video...")
        final_path = os.path.join(work_dir, "final.mp4")
        total_duration = await wan_compose(
            scene_clips=scene_clips,
            scene_audio=scene_audio,
            scene_durations=scene_durations,
            output_path=final_path,
            transitions=[s.transition_in for s in video_plan.scenes],
            music_mood=video_plan.audio.music_mood,
            work_dir=work_dir,
        )
        timings["compose"] = time.monotonic() - t0
        size_mb = os.path.getsize(final_path) / 1e6

        # ── Stage 5: Upload ───────────────────────────────────────────────────
        await report(94, "Uploading...")
        cloudinary_url: Optional[str] = None
        cloudinary_public_id: Optional[str] = None

        if is_cloudinary_configured():
            try:
                cloudinary_url, cloudinary_public_id = await upload_video_file(
                    final_path, project_id, job_id
                )
            except CloudinaryError as e:
                logger.warning(f"Cloudinary upload failed: {e}. Keeping local file.")
        else:
            logger.info("Cloudinary not configured — video stays local")

        if not cloudinary_url and os.path.exists(final_path):
            local_dir = os.path.abspath(os.path.join("storage", "outputs"))
            os.makedirs(local_dir, exist_ok=True)
            persistent_path = os.path.join(local_dir, f"{job_id}.mp4")
            shutil.copy2(final_path, persistent_path)
            video_url = f"file:///{persistent_path.replace(os.sep, '/')}"
        else:
            video_url = cloudinary_url or f"file:///{final_path.replace(os.sep, '/')}"

        timings["total"] = time.monotonic() - t0

        # Thumbnail URL from Cloudinary
        thumb = None
        if cloudinary_url and "/upload/" in cloudinary_url:
            thumb = cloudinary_url.replace("/upload/", "/upload/so_1.0,w_540/").rsplit(".", 1)[0] + ".jpg"

        logger.info(
            f"[{job_id}] Wan pipeline complete in {timings['total']:.1f}s "
            f"— {total_duration:.1f}s video, {size_mb:.1f} MB: {video_url}"
        )

        return {
            "cloudinary_url": cloudinary_url,
            "cloudinary_public_id": cloudinary_public_id,
            "original_url": video_url,
            "thumbnail_url": thumb,
            "duration_seconds": round(total_duration, 1),
            "file_size_mb": round(size_mb, 2),
            "shots": total_scenes,
            "engine": "wan" if s.VIDEO_ENGINE == "wan" else "native",
            "timings": {k: round(v, 1) for k, v in timings.items()},
        }


async def _generate_scene_with_retry(
    engine,
    scene: Scene,
    video_plan: VideoPlan,
    work_dir: str,
    index: int,
    max_attempts: int = 2,
) -> str:
    """Generate a single scene, retrying on failure.

    On the second attempt, drops any reference image (falls back from I2V to T2V).

    Returns:
        Path to the generated clip MP4.

    Raises:
        WanError: If all attempts fail.
    """
    s = get_settings()
    w, h = _aspect_to_dims(video_plan.aspect_ratio, s.WAN_MODEL_SIZE)
    output_path = os.path.join(work_dir, "scenes", f"scene_{index:03d}.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prompt = _build_scene_prompt(scene, video_plan.style)
    last_error = None

    for attempt in range(max_attempts):
        # Drop reference image on retry (I2V → T2V fallback)
        ref_image = scene.reference_image if attempt == 0 else None

        try:
            path = await engine.generate_scene(
                prompt=prompt,
                image=ref_image,
                duration=scene.duration,
                width=w,
                height=h,
                fps=video_plan.fps,
                output_path=output_path,
                aspect_ratio=video_plan.aspect_ratio,
            )
            return path
        except Exception as e:
            last_error = e
            logger.warning(
                f"Scene {index + 1} attempt {attempt + 1} failed: {e}. "
                f"{'Retrying without reference image.' if attempt == 0 and ref_image else 'No more retries.'}"
            )
            await asyncio.sleep(2)

    raise WanError(
        f"Scene {index + 1} ({scene.id}) failed after {max_attempts} attempts. "
        f"Last error: {last_error}",
        scene_id=scene.id,
    )


def _build_scene_prompt(scene: Scene, global_style: str) -> str:
    """Combine scene visual_prompt, motion_prompt, camera, and style into one prompt."""
    style = scene.style or global_style
    camera_desc = (
        f"{scene.camera.shot_type} shot, {scene.camera.movement} camera movement, "
        f"{scene.camera.angle} angle"
    )
    parts = [
        scene.visual_prompt,
        scene.motion_prompt,
        camera_desc,
        style,
    ]
    return ", ".join(p.strip() for p in parts if p.strip())


def _aspect_to_dims(aspect_ratio: str, model_size: str) -> tuple:
    """Get (width, height) for the given aspect ratio and model size."""
    size = model_size.lower()
    if size in ("720p",):
        base_long, base_short = 1280, 720
    elif size in ("1.3b",):
        base_long, base_short = 832, 480
    else:  # 480P default
        base_long, base_short = 832, 480

    if aspect_ratio == "9:16":
        return base_short, base_long
    elif aspect_ratio == "1:1":
        return base_short, base_short
    else:  # 16:9
        return base_long, base_short
