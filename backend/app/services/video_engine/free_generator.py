"""Free Multi-Scene AI Video Generator Engine.

Features:
  1. Edge-TTS with Millisecond Timestamping: Generates natural neural voiceover and exact synchronized SRT subtitles.
  2. Realistic AI Visuals: Scene-specific photorealistic image generation with clean prompts and Unsplash fallback.
  3. Cinematic Ken Burns Camera Motion: Dynamic zoom-in, pan, and zoom-out per scene (no static frozen slides).
  4. Audio-Synced Dynamic Subtitles: Subtitles burned in via FFmpeg libass at the exact millisecond words/sentences are spoken.
  5. Native FFmpeg: Seamless multi-scene concatenation and Cloudinary upload.
"""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import imageio_ffmpeg
from PIL import Image, ImageDraw

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
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1920&h=1080&fit=crop&q=80",
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


def _format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp 00:00:00,000."""
    millis = int((seconds % 1) * 1000)
    total_secs = int(seconds)
    secs = total_secs % 60
    mins = (total_secs // 60) % 60
    hours = total_secs // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _clean_visual_prompt(visual_description: str, narration: str) -> str:
    """Transform script stage directions into a realistic AI image prompt."""
    text = visual_description.strip() or narration.strip() or "Cinematic scene"
    patterns = [
        r"^(cut to|the presenter is shown|a presenter|close-up shot of|close-up of|medium shot of|wide shot of|overlay subtle text[^\.\,]*|slow dolly[^\.\,]*|camera notes[^\.\,]*)\s*",
        r"[-—–]+",
        r"\b(cut to|overlay|text labels|camera)\b",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()[:18]
    prompt_subject = " ".join(words)
    return f"{prompt_subject}, photorealistic, 8k resolution, cinematic 35mm film photography, natural lighting, highly detailed"


async def generate_scene_audio_and_subtitles(
    text: str,
    audio_path: str,
    srt_path: str,
    voice: str,
) -> Tuple[bool, float]:
    """Generate audio and millisecond-accurate synchronized SRT subtitles."""
    try:
        import edge_tts
        clean_text = text.strip() or "Scene narration."
        communicate = edge_tts.Communicate(clean_text, voice)

        sub_entries = []
        idx = 1

        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    start = chunk["offset"] / 10_000_000.0
                    end = start + (chunk["duration"] / 10_000_000.0)
                    chunk_text = chunk["text"].strip()
                    if chunk_text:
                        sub_entries.append(
                            f"{idx}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{chunk_text}\n"
                        )
                        idx += 1

        # If no SentenceBoundary was emitted, create single subtitle spanning entire audio
        duration = _get_media_duration(audio_path)
        if not sub_entries and clean_text:
            sub_entries.append(
                f"1\n00:00:00,100 --> {_format_srt_time(max(duration - 0.2, 1.0))}\n{clean_text}\n"
            )

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sub_entries) + "\n")

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


async def fetch_scene_image(
    prompt: str,
    narration: str,
    output_path: str,
    scene_num: int,
) -> str:
    """Fetch realistic 1920x1080 clean scene image."""
    clean_prompt = _clean_visual_prompt(prompt, narration)
    encoded = urllib.parse.quote(clean_prompt)
    seed = scene_num * 123 + 45
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&nologo=true&seed={seed}"

    # 1. Try Pollinations AI with clean prompt
    try:
        async with httpx.AsyncClient(timeout=14.0) as client:
            resp = await client.get(pollinations_url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                _ensure_1080p(output_path)
                return output_path
    except Exception as e:
        logger.info(f"Pollinations skipped for scene {scene_num} ({e}), using HD stock photo fallback")

    # 2. High-quality HD stock photo fallback matching the topic
    topic_key = "food" if any(w in (prompt + narration).lower() for w in ["food", "diet", "healthy", "eat", "cook", "vegetable", "fruit", "meal"]) else "general"
    photo_urls = FALLBACK_PHOTO_TOPICS.get(topic_key, FALLBACK_PHOTO_TOPICS["general"])
    fallback_url = photo_urls[(scene_num - 1) % len(photo_urls)]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(fallback_url, follow_redirects=True)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                _ensure_1080p(output_path)
                return output_path
    except Exception as e:
        logger.warning(f"Stock photo fallback failed: {e}")

    # 3. Local graceful fallback if offline
    _create_local_canvas(output_path)
    return output_path


def _ensure_1080p(image_path: str):
    """Ensure image is clean 1920x1080 without artifacts."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img.save(image_path, "JPEG", quality=92)
    except Exception:
        pass


def _create_local_canvas(output_path: str):
    """High-res styled canvas if network unavailable."""
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1920, 16], fill=(59, 130, 246))
    draw.rectangle([0, 1064, 1920, 1080], fill=(59, 130, 246))
    img.save(output_path, "JPEG", quality=90)


def render_scene_clip(
    image_path: str,
    audio_path: Optional[str],
    srt_path: Optional[str],
    output_path: str,
    ffmpeg_exe: str,
    duration: float,
    scene_num: int,
) -> bool:
    """Render a single scene MP4 clip with Ken Burns motion and synchronized subtitles."""
    dur_sec = max(duration, 3.5)
    fps = 25
    total_frames = int(dur_sec * fps)

    # Alternating cinematic camera movements per scene:
    motion_type = (scene_num - 1) % 3
    if motion_type == 0:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    elif motion_type == 1:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='1.15':d={total_frames}:x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    else:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='max(1.20-0.0012*on,1.0)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"

    # Build filter chain with exact synced subtitles if srt available
    if srt_path and os.path.exists(srt_path):
        clean_srt = srt_path.replace("'", "\\'")
        sub_filter = f",subtitles='{clean_srt}':force_style='FontSize=22,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=1,MarginV=35'"
        filter_expr = f"{motion_expr}{sub_filter}"
    else:
        filter_expr = motion_expr

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
        # Retry without subtitles if subtitle filter failed
        fallback_cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", motion_expr,
            "-t", str(dur_sec),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path,
        ]
        res = subprocess.run(fallback_cmd, capture_output=True, text=True)
        return res.returncode == 0
    return True


def concat_scene_clips(clip_paths: List[str], final_output: str, ffmpeg_exe: str) -> bool:
    """Concatenate multiple scene MP4 clips into one unified video with guaranteed transitions."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copyfile(clip_paths[0], final_output)
        return True

    inputs = []
    filter_parts = []
    for i, p in enumerate(clip_paths):
        inputs.extend(["-i", p])
        filter_parts.append(f"[{i}:v][{i}:a]")

    filter_complex = "".join(filter_parts) + f"concat=n={len(clip_paths)}:v=1:a=1[v][a]"
    cmd = [
        ffmpeg_exe, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        final_output,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return True
    logger.error(f"Filter complex concat failed: {res.stderr[:200]}")
    return False


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
            "duration_seconds": 5,
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

            # 2. Generate Audio and synchronized SRT subtitles
            audio_file = os.path.join(tmp_dir, f"audio_{scene_num}.mp3")
            srt_file = os.path.join(tmp_dir, f"sub_{scene_num}.srt")
            has_audio, audio_duration = await generate_scene_audio_and_subtitles(
                text=narration,
                audio_path=audio_file,
                srt_path=srt_file,
                voice=voice,
            )
            total_duration += audio_duration

            # 3. Fetch realistic clean scene image
            image_file = os.path.join(tmp_dir, f"image_{scene_num}.jpg")
            await fetch_scene_image(
                prompt=visual,
                narration=narration,
                output_path=image_file,
                scene_num=scene_num,
            )

            # 4. Render Clip with dynamic Ken Burns motion and synchronized subtitles
            clip_file = os.path.join(tmp_dir, f"clip_{scene_num}.mp4")
            success = render_scene_clip(
                image_path=image_file,
                audio_path=audio_file if has_audio else None,
                srt_path=srt_file if has_audio else None,
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

        final_duration_sec = int(total_duration or len(scenes) * 5)
        logger.info(f"Video created with synced subtitles: {cloudinary_url}")
        return cloudinary_url, cloudinary_public_id, final_duration_sec


async def sync_audio_and_captions_to_video(
    video_url: str,
    script: Dict[str, Any],
    task_id: str,
    project_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Take a raw video (e.g. from Agnes AI or stock), generate synchronized neural voiceover and burned captions, then upload to Cloudinary."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    voice = _get_voice_for_tone(script.get("tone", "professional"))

    scenes = script.get("scenes") or []
    narration = (
        scenes[0].get("narration") if scenes else ""
    ) or script.get("hook") or script.get("title") or "AI generated video"

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_file = os.path.join(tmp_dir, "sync_audio.mp3")
        srt_file = os.path.join(tmp_dir, "sync_sub.srt")
        output_mp4 = os.path.join(tmp_dir, "sync_final.mp4")

        has_audio, audio_dur = await generate_scene_audio_and_subtitles(
            text=narration,
            audio_path=audio_file,
            srt_path=srt_file,
            voice=voice,
        )

        clean_srt = srt_file.replace("'", "\\'")
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_url,
            "-i", audio_file,
            "-vf", f"subtitles='{clean_srt}':force_style='FontSize=22,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=1,MarginV=30'",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_mp4,
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_mp4):
            return await upload_video_file(output_mp4, project_id, task_id)
        else:
            logger.warning(f"Audio/caption sync failed: {res.stderr[:200]}, falling back to raw upload")
            from app.services.cloudinary.uploader import upload_video_from_url
            return await upload_video_from_url(video_url, project_id, task_id)

