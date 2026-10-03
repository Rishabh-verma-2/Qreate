"""Free Multi-Scene AI Video Generator Engine.

Features:
  1. Edge-TTS: Natural Microsoft Neural voiceover per scene.
  2. Realistic AI Visuals: Scene-specific photorealistic image generation with clean prompts and Unsplash fallback.
  3. Cinematic Ken Burns Camera Motion: Dynamic zoom-in, pan, and zoom-out per scene (no static frozen slides).
  4. Caption Overlay: Clean modern subtitles with narration on screen.
  5. Native FFmpeg: Seamless multi-scene concatenation and Cloudinary upload.
"""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import textwrap
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from app.database import crud
from app.services.cloudinary.uploader import upload_video_file

logger = logging.getLogger(__name__)

# Recommended free neural voices
DEFAULT_VOICES = {
    "professional": "en-US-ChristopherNeural",
    "friendly": "en-US-JennyNeural",
    "energetic": "en-US-GuyNeural",
    "calm": "en-US-AriaNeural",
    "dramatic": "en-GB-RyanNeural",
}

# Thematic photorealistic stock photos for reliable fallback
FALLBACK_PHOTO_TOPICS = {
    "food": [
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1920&h=1080&fit=crop&q=80", # Healthy fruits
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1920&h=1080&fit=crop&q=80", # Salad & greens
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1920&h=1080&fit=crop&q=80", # Nutritious meal
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1920&h=1080&fit=crop&q=80", # Fresh bowl
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1920&h=1080&fit=crop&q=80", # Avocado & toast
    ],
    "tech": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1920&h=1080&fit=crop&q=80",
    ],
    "general": [
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1920&h=1080&fit=crop&q=80",
    ],
}


def _get_voice_for_tone(tone: str) -> str:
    t = (tone or "professional").lower()
    return DEFAULT_VOICES.get(t, "en-US-ChristopherNeural")


def _clean_visual_prompt(visual_description: str, narration: str) -> str:
    """Transform script stage directions into a realistic AI image prompt."""
    text = visual_description.strip() or narration.strip() or "Cinematic scene"
    # Remove script directions
    patterns = [
        r"^(cut to|the presenter is shown|a presenter|close-up shot of|close-up of|medium shot of|wide shot of|overlay subtle text[^\.\,]*|slow dolly[^\.\,]*|camera notes[^\.\,]*)\s*",
        r"[-—–]+",
        r"\b(cut to|overlay|text labels|camera)\b",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)

    # Condense multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()[:18]
    prompt_subject = " ".join(words)

    # Append high quality photographic keywords
    return f"{prompt_subject}, photorealistic, 8k resolution, cinematic 35mm film photography, natural lighting, highly detailed"


async def generate_scene_audio(text: str, output_path: str, voice: str) -> Tuple[bool, float]:
    """Generate voiceover audio using edge-tts and get duration."""
    try:
        import edge_tts
        clean_text = text.strip() or "Scene narration."
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(output_path)

        # Get exact audio duration
        duration = _get_media_duration(output_path)
        return True, max(duration, 3.0)
    except Exception as e:
        logger.warning(f"Edge-TTS failed: {e}, using fallback duration")
        return False, 5.0


def _get_media_duration(file_path: str) -> float:
    """Probe audio/video duration using FFmpeg."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        res = subprocess.run([ffmpeg_exe, "-i", file_path], capture_output=True, text=True)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 5.0


def _draw_subtitles_on_image(image_path: str, narration: str):
    """Overlay clean, modern subtitles at the bottom center of the image."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            # Ensure 1920x1080 high-res canvas for camera motion
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(img)

            # Format subtitle text
            clean_text = narration.strip()
            if clean_text:
                wrapped_lines = textwrap.wrap(clean_text, width=48)[:3]
                text_to_show = "\n".join(wrapped_lines)

                # Modern dark pill container at bottom center
                line_height = 36
                box_height = len(wrapped_lines) * line_height + 40
                box_y1 = 1080 - box_height - 60
                box_y2 = 1080 - 60
                box_x1 = 160
                box_x2 = 1760

                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.rounded_rectangle(
                    [box_x1, box_y1, box_x2, box_y2],
                    radius=18,
                    fill=(10, 15, 30, 205),
                )
                img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                draw = ImageDraw.Draw(img)

                # Draw subtitle text
                curr_y = box_y1 + 20
                for line in wrapped_lines:
                    draw.text(
                        (960, curr_y),
                        line,
                        fill=(255, 255, 255),
                        anchor="mt",
                    )
                    curr_y += line_height

            img.save(image_path, "JPEG", quality=92)
    except Exception as e:
        logger.warning(f"Subtitle overlay error: {e}")


async def fetch_scene_image(
    prompt: str,
    narration: str,
    output_path: str,
    scene_num: int,
    script_topic: str = "food",
) -> str:
    """Fetch realistic scene image with automatic photographic fallback."""
    clean_prompt = _clean_visual_prompt(prompt, narration)
    encoded = urllib.parse.quote(clean_prompt)
    seed = scene_num * 123 + 45
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&seed={seed}"

    # 1. Try Pollinations AI with clean prompt
    try:
        async with httpx.AsyncClient(timeout=14.0) as client:
            resp = await client.get(pollinations_url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                _draw_subtitles_on_image(output_path, narration)
                return output_path
    except Exception as e:
        logger.info(f"Pollinations skipped for scene {scene_num} ({e}), using HD stock photography fallback")

    # 2. High-quality HD stock photo fallback matching the topic
    topic_key = "food" if any(w in (prompt + narration).lower() for w in ["food", "diet", "healthy", "eat", "cook", "vegetable", "fruit", "meal"]) else "general"
    photo_urls = FALLBACK_PHOTO_TOPICS.get(topic_key, FALLBACK_PHOTO_TOPICS["food"])
    fallback_url = photo_urls[(scene_num - 1) % len(photo_urls)]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(fallback_url, follow_redirects=True)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                _draw_subtitles_on_image(output_path, narration)
                return output_path
    except Exception as e:
        logger.warning(f"Stock photo fallback failed: {e}")

    # 3. Local graceful fallback if offline
    _create_local_canvas(output_path, clean_prompt, narration, scene_num)
    return output_path


def _create_local_canvas(output_path: str, prompt: str, narration: str, scene_num: int):
    """High-res styled canvas if network unavailable."""
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    # Accent top and bottom cinematic border
    draw.rectangle([0, 0, 1920, 16], fill=(59, 130, 246))
    draw.rectangle([0, 1064, 1920, 1080], fill=(59, 130, 246))
    img.save(output_path, "JPEG", quality=90)
    _draw_subtitles_on_image(output_path, narration)


def render_scene_clip(
    image_path: str,
    audio_path: Optional[str],
    output_path: str,
    ffmpeg_exe: str,
    duration: float,
    scene_num: int,
) -> bool:
    """Render a single scene MP4 clip with cinematic Ken Burns camera motion."""
    dur_sec = max(duration, 3.5)
    fps = 25
    total_frames = int(dur_sec * fps)

    # Alternating cinematic camera movements per scene:
    # Scene 1: Smooth camera push-in
    # Scene 2: Smooth camera pan left-to-right
    # Scene 3: Smooth camera zoom-out
    motion_type = (scene_num - 1) % 3
    if motion_type == 0:
        # Camera push-in
        filter_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    elif motion_type == 1:
        # Camera pan across
        filter_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='1.15':d={total_frames}:x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    else:
        # Camera zoom-out
        filter_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='max(1.20-0.0012*on,1.0)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"

    if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", filter_expr,
            "-t", str(dur_sec),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
    else:
        cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", filter_expr,
            "-t", str(dur_sec),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path,
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f"FFmpeg scene {scene_num} render error: {res.stderr[:250]}")
        return False
    return True


def concat_scene_clips(clip_paths: List[str], final_output: str, ffmpeg_exe: str) -> bool:
    """Concatenate multiple scene MP4 clips into one unified video."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copyfile(clip_paths[0], final_output)
        return True

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_file = f.name
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    try:
        cmd = [
            ffmpeg_exe, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            final_output,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)


async def generate_free_video(
    task_id: str,
    project_id: str,
    script: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], Any]] = None,
) -> Tuple[str, str, int]:
    """Generate a complete multi-scene video using free tools and upload to Cloudinary.

    Returns:
        (cloudinary_url, cloudinary_public_id, duration_seconds)
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = script.get("scenes") or []
    if not scenes:
        scenes = [{
            "scene_number": 1,
            "narration": script.get("hook") or script.get("title") or "Healthy eating benefits",
            "visual_description": script.get("title") or "Healthy food kitchen nutrition",
            "duration_seconds": 6,
        }]

    voice = _get_voice_for_tone(script.get("tone", "professional"))

    with tempfile.TemporaryDirectory() as tmp_dir:
        clip_paths: List[str] = []
        total_scenes = len(scenes)
        total_duration = 0.0

        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            narration = scene.get("narration", "")
            visual = scene.get("visual_description", "")

            # 1. Update progress
            pct = int(10 + (i / total_scenes) * 65)
            if progress_callback:
                await progress_callback(pct, f"Rendering Scene {scene_num}/{total_scenes}")

            # 2. Generate Audio and get exact length
            audio_file = os.path.join(tmp_dir, f"audio_{scene_num}.mp3")
            has_audio, audio_duration = await generate_scene_audio(narration, audio_file, voice)
            total_duration += audio_duration

            # 3. Fetch realistic scene image with subtitles
            image_file = os.path.join(tmp_dir, f"image_{scene_num}.jpg")
            await fetch_scene_image(
                prompt=visual,
                narration=narration,
                output_path=image_file,
                scene_num=scene_num,
            )

            # 4. Render Clip with dynamic Ken Burns camera motion
            clip_file = os.path.join(tmp_dir, f"clip_{scene_num}.mp4")
            success = render_scene_clip(
                image_path=image_file,
                audio_path=audio_file if has_audio else None,
                output_path=clip_file,
                ffmpeg_exe=ffmpeg_exe,
                duration=audio_duration,
                scene_num=scene_num,
            )
            if success and os.path.exists(clip_file):
                clip_paths.append(clip_file)

        if not clip_paths:
            raise RuntimeError("Failed to render any scene clips")

        # 5. Assemble final video
        if progress_callback:
            await progress_callback(85, "Assembling scenes into final video...")

        final_mp4 = os.path.join(tmp_dir, "final_video.mp4")
        concat_scene_clips(clip_paths, final_mp4, ffmpeg_exe)

        # 6. Upload to Cloudinary
        if progress_callback:
            await progress_callback(92, "Uploading to Cloudinary...")

        cloudinary_url, cloudinary_public_id = await upload_video_file(
            file_path=final_mp4,
            project_id=project_id,
            task_id=task_id,
        )

        final_duration_sec = int(total_duration or len(scenes) * 6)
        logger.info(f"Video created with realistic visuals & motion: {cloudinary_url}")
        return cloudinary_url, cloudinary_public_id, final_duration_sec
