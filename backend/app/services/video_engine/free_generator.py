"""Animation-First Multi-Scene Video Generator Engine.

Architecture:
  For each scene:
    1. Generate TTS audio + word-boundary SRT subtitles (Edge-TTS)
    2. Detect animation concept key from scene metadata (motion_graphics.detect_concept_key)
    3. If concept found → render procedural animated MP4 (motion_graphics.render_motion_graphic_clip)
       Else → fetch scene photograph (Agnes AI → Openverse → Wikimedia → stock fallback)
    4. Mux audio + SRT into the animated/photo clip (FFmpeg)
  5. Concatenate all scene clips → final MP4
  6. Upload to Cloudinary

This connects the existing 2444-line motion_graphics.py engine to actual video output.
Previously, motion_graphics was completely disconnected — every scene used Ken Burns on a photo.
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

from app.core.config import settings
from app.services.cloudinary.uploader import upload_video_file
from app.services.purffle.motion_graphics import detect_concept_key, render_motion_graphic_clip

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# VOICE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_VOICES = {
    "professional": "en-US-ChristopherNeural",
    "friendly": "en-US-JennyNeural",
    "energetic": "en-US-GuyNeural",
    "calm": "en-US-AriaNeural",
    "dramatic": "en-GB-RyanNeural",
    "educational": "en-US-ChristopherNeural",
    "cinematic": "en-GB-RyanNeural",
    "inspirational": "en-US-AriaNeural",
    "conversational": "en-US-JennyNeural",
    "mysterious": "en-GB-RyanNeural",
    "high_energy": "en-US-GuyNeural",
    "entertaining": "en-US-GuyNeural",
}

# Thematic stock photo fallbacks for non-animatable scenes
FALLBACK_PHOTO_TOPICS = {
    "cars": [
        "https://images.unsplash.com/photo-1617788138017-80ad40651399?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=1920&h=1080&fit=crop&q=80",
    ],
    "tech": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1920&h=1080&fit=crop&q=80",
    ],
    "business": [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1920&h=1080&fit=crop&q=80",
    ],
    "fitness": [
        "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1920&h=1080&fit=crop&q=80",
    ],
    "food": [
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1920&h=1080&fit=crop&q=80",
    ],
    "travel": [
        "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1920&h=1080&fit=crop&q=80",
    ],
    "general": [
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1920&h=1080&fit=crop&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1920&h=1080&fit=crop&q=80",
    ],
}


def _get_voice_for_tone(tone: Any) -> str:
    if isinstance(tone, (list, tuple)):
        tone = tone[0] if tone else "professional"
    t = str(tone or "professional").strip().lower()
    return DEFAULT_VOICES.get(t, "en-US-ChristopherNeural")


def _format_srt_time(seconds: float) -> str:
    millis = int((seconds % 1) * 1000)
    total_secs = int(seconds)
    secs = total_secs % 60
    mins = (total_secs // 60) % 60
    hours = total_secs // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _get_media_duration(file_path: str) -> float:
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


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO + SRT GENERATION (Edge-TTS with word-boundary timestamps)
# ─────────────────────────────────────────────────────────────────────────────

async def generate_scene_audio_and_subtitles(
    text: str,
    audio_path: str,
    srt_path: str,
    voice: str,
) -> Tuple[bool, float]:
    """Generate neural TTS audio and millisecond-accurate word-by-word SRT subtitles."""
    try:
        import edge_tts
        clean_text = text.strip() or "Scene narration."
        communicate = edge_tts.Communicate(clean_text, voice, boundary="WordBoundary")

        words = []
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 10_000_000.0
                    dur = chunk["duration"] / 10_000_000.0
                    w_text = chunk["text"].strip()
                    if w_text:
                        words.append({"start": start, "end": start + dur, "text": w_text})

        duration = _get_media_duration(audio_path)

        # Build punchy word-by-word subtitle cues (Shorts/TikTok style)
        sub_entries = []
        if words:
            cues = []
            i = 0
            glue = {"the", "a", "an", "to", "in", "of", "for", "on", "with", "at", "is", "and", "by", "its", "it"}
            while i < len(words):
                curr = words[i]
                if i < len(words) - 1 and (len(curr["text"]) <= 2 or curr["text"].lower() in glue):
                    nxt = words[i + 1]
                    cues.append({
                        "start": curr["start"],
                        "end": nxt["end"],
                        "text": f"{curr['text']} {nxt['text']}".upper()
                    })
                    i += 2
                else:
                    cues.append({
                        "start": curr["start"],
                        "end": curr["end"],
                        "text": curr["text"].upper()
                    })
                    i += 1

            for idx, cue in enumerate(cues):
                s = cue["start"]
                if idx < len(cues) - 1:
                    e = min(cues[idx + 1]["start"], cue["end"] + 0.08)
                    e = max(e, s + 0.15)
                else:
                    e = min(duration, cue["end"] + 0.3)
                sub_entries.append(
                    f"{idx + 1}\n{_format_srt_time(s)} --> {_format_srt_time(e)}\n{cue['text']}\n"
                )
        elif clean_text:
            sub_entries.append(
                f"1\n00:00:00,100 --> {_format_srt_time(max(duration - 0.2, 1.0))}\n{clean_text.upper()}\n"
            )

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sub_entries) + "\n")

        return True, max(duration, 3.0)
    except Exception as e:
        logger.warning(f"Edge-TTS failed: {e}, using fallback duration")
        return False, 5.0


# ─────────────────────────────────────────────────────────────────────────────
# MOTION GRAPHIC SCENE RENDERING (animation-first path)
# ─────────────────────────────────────────────────────────────────────────────

def render_animated_scene_clip(
    concept_key: str,
    audio_path: Optional[str],
    srt_path: Optional[str],
    output_path: str,
    ffmpeg_exe: str,
    duration: float,
    scene_num: int,
    title: str,
    narration: str,
    scene_metadata: Dict[str, Any],
    aspect_ratio: str = "9:16",
) -> bool:
    """Render an animated motion graphic scene and mux audio + subtitles into it.

    Steps:
      1. render_motion_graphic_clip → silent animated 1080x1920 MP4
      2. FFmpeg mux: animated video + audio + SRT subtitles → final clip
    """
    dur_sec = max(duration, 3.5)
    silent_mp4 = output_path.replace(".mp4", "_silent.mp4")

    # Step 1: Render animated frames
    logger.info(f"[Scene {scene_num}] Rendering animated motion graphic: concept='{concept_key}'")
    ok = render_motion_graphic_clip(
        concept_key=concept_key,
        output_mp4_path=silent_mp4,
        duration_seconds=dur_sec,
        title=title,
        narration=narration,
        scene_metadata=scene_metadata,
    )

    if not ok or not os.path.isfile(silent_mp4):
        logger.warning(f"[Scene {scene_num}] Motion graphic render failed for '{concept_key}'")
        return False

    # Step 2: Mux audio + SRT into the animated clip
    has_audio = audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
    has_srt = srt_path and os.path.exists(srt_path)

    # Build subtitle filter string if available
    sub_filter = ""
    if has_srt:
        clean_srt = srt_path.replace("'", "\\'")
        sub_filter = (
            f",subtitles='{clean_srt}':force_style="
            f"'FontSize=26,FontName=Arial,Bold=1,PrimaryColour=&H0000FFFF,"
            f"BackColour=&H80000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=60'"
        )

    # Dynamic target resolution based on aspect ratio
    tw, th = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    scale_filter = f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2{sub_filter}"

    if has_audio:
        cmd = [
            ffmpeg_exe, "-y",
            "-i", silent_mp4,
            "-i", audio_path,
            "-vf", scale_filter,
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
            "-i", silent_mp4,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", scale_filter,
            "-t", str(dur_sec),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path,
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f"[Scene {scene_num}] FFmpeg mux failed: {res.stderr[:300]}")
        # Retry without subtitles
        if has_srt:
            cmd_nosub = [x for x in cmd if "subtitles=" not in x]
            # Rebuild scale without sub filter
            cmd_nosub = [
                ffmpeg_exe, "-y",
                "-i", silent_mp4,
                "-i" if has_audio else "-f", audio_path if has_audio else "lavfi",
            ]
            if not has_audio:
                cmd_nosub += ["-i", "anullsrc=r=44100:cl=stereo"]
            else:
                cmd_nosub += ["-i", audio_path]
            cmd_nosub += [
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-t", str(dur_sec),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path,
            ]
            res2 = subprocess.run(cmd_nosub, capture_output=True, text=True)
            if res2.returncode == 0 and os.path.exists(output_path):
                logger.info(f"[Scene {scene_num}] Rendered animated clip without subtitles")
                return True
        return False

    # Clean up silent intermediate
    try:
        os.remove(silent_mp4)
    except Exception:
        pass

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


# ─────────────────────────────────────────────────────────────────────────────
# PHOTO/STOCK SCENE RENDERING (fallback for non-animatable scenes)
# ─────────────────────────────────────────────────────────────────────────────

def render_scene_clip(
    image_path: str,
    audio_path: Optional[str],
    srt_path: Optional[str],
    output_path: str,
    ffmpeg_exe: str,
    duration: float,
    scene_num: int,
) -> bool:
    """Render a Ken Burns photo clip (fallback when no concept animation available)."""
    dur_sec = max(duration, 3.5)
    fps = 25
    total_frames = int(dur_sec * fps)

    # Alternating cinematic camera movements
    motion_type = (scene_num - 1) % 3
    if motion_type == 0:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    elif motion_type == 1:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='1.15':d={total_frames}:x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"
    else:
        motion_expr = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='max(1.20-0.0012*on,1.0)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}"

    if srt_path and os.path.exists(srt_path):
        clean_srt = srt_path.replace("'", "\\'")
        sub_filter = (
            f",subtitles='{clean_srt}':force_style="
            f"'FontSize=28,FontName=Arial,Bold=1,PrimaryColour=&H0000FFFF,BackColour=&H80000000,"
            f"BorderStyle=3,Outline=3,Shadow=2,Alignment=2,MarginV=55'"
        )
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


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE FETCHING (for photo fallback scenes)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_search_keywords(visual_description: str, narration: str, script_title: str = "") -> str:
    text = visual_description.strip() or narration.strip()
    patterns = [
        r"(?i)\b(cut to|the presenter is shown|a presenter|close-up shot of|close-up of|medium shot of|wide shot of|slow cinematic pan across|slow pan across|dark moody reveal of|dramatic reveal of|montage of|quick cuts across|tracking shot of|heroic pose against|shown in|shown from)\b",
        r"(?i)\b(text overlay|text labels|overlay subtle text|overlay|screen shows|lower third)[^.]*?(?=\.|$|\n)",
        r"[\$€£]\d+[\w\s—–-]*",
        r"[-—–:]+",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    stopwords = {
        "the", "a", "an", "in", "on", "at", "with", "from", "of", "and", "for",
        "is", "are", "shown", "each", "all", "its", "their", "this", "that",
        "these", "those", "into", "over", "under", "next", "to", "across", "heroic"
    }
    words = [w for w in cleaned.split() if len(w) > 1 and w.lower() not in stopwords]
    query = " ".join(words[:4])
    return query or script_title or "cinematic"


def _clean_visual_prompt(visual_description: str, narration: str, script_title: str = "") -> str:
    text = visual_description.strip() or narration.strip() or script_title or "Cinematic scene"
    patterns = [
        r"^(cut to|the presenter is shown|a presenter|close-up shot of|close-up of|medium shot of|wide shot of|overlay subtle text[^\.,]*|slow dolly[^\.,]*|camera notes[^\.,]*)\s*",
        r"[-—–]+",
        r"\b(cut to|overlay|text labels|camera)\b",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()[:20]
    prompt_subject = " ".join(words)
    return f"{prompt_subject}, photorealistic, 8k resolution, cinematic 35mm film photography, natural lighting, highly detailed"


async def _generate_agnes_ai_image(prompt: str, output_path: str) -> bool:
    if not settings.AGNES_API_KEY:
        return False
    url = f"{settings.AGNES_BASE_URL.rstrip('/')}/v1/images/generations"
    headers = {"Authorization": f"Bearer {settings.AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": settings.AGNES_IMAGE_MODEL or "agnes-image-2.5-flash",
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data") or []
                if items and items[0].get("url"):
                    img_url = items[0]["url"]
                    dl_resp = await client.get(img_url, timeout=15.0)
                    if dl_resp.status_code == 200 and len(dl_resp.content) > 5000:
                        with open(output_path, "wb") as f:
                            f.write(dl_resp.content)
                        _ensure_1080p(output_path)
                        return True
    except Exception as e:
        logger.warning(f"Agnes image generation skipped: {e}")
    return False


async def _fetch_openverse_image(
    keywords: str, output_path: str, scene_num: int, used_sources: Optional[set] = None
) -> bool:
    url = f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(keywords)}&page_size=8"
    headers = {"User-Agent": "QreateApp/1.0 (free-generator@qreate.local)"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results") or []
                if results:
                    if used_sources is not None:
                        available = [r for r in results if r.get("url") and r.get("url") not in used_sources]
                        choice = available[0] if available else results[(scene_num - 1) % len(results)]
                    else:
                        choice = results[(scene_num - 1) % len(results)]
                    img_url = choice.get("url")
                    if img_url:
                        dl_resp = await client.get(img_url, headers=headers, timeout=12.0, follow_redirects=True)
                        if dl_resp.status_code == 200 and len(dl_resp.content) > 5000:
                            with open(output_path, "wb") as f:
                                f.write(dl_resp.content)
                            _ensure_1080p(output_path)
                            if used_sources is not None:
                                used_sources.add(img_url)
                            return True
    except Exception as e:
        logger.info(f"Openverse search skipped for '{keywords}': {e}")
    return False


async def _fetch_wikimedia_image(
    keywords: str, output_path: str, used_sources: Optional[set] = None
) -> bool:
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrnamespace=6&gsrsearch={urllib.parse.quote(keywords)}&gsrlimit=4"
        f"&prop=imageinfo&iiprop=url&iiurlwidth=1920&format=json"
    )
    headers = {"User-Agent": "QreateApp/1.0 (contact@qreate.local)"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    info_list = p.get("imageinfo") or []
                    if info_list:
                        thumb = info_list[0].get("thumburl") or info_list[0].get("url")
                        if thumb and (used_sources is None or thumb not in used_sources) and any(ext in thumb.lower() for ext in [".jpg", ".jpeg", ".png"]):
                            dl_resp = await client.get(thumb, headers=headers, timeout=12.0, follow_redirects=True)
                            if dl_resp.status_code == 200 and len(dl_resp.content) > 5000:
                                with open(output_path, "wb") as f:
                                    f.write(dl_resp.content)
                                _ensure_1080p(output_path)
                                if used_sources is not None:
                                    used_sources.add(thumb)
                                return True
    except Exception as e:
        logger.info(f"Wikimedia search skipped for '{keywords}': {e}")
    return False


async def fetch_scene_image(
    prompt: str,
    narration: str,
    output_path: str,
    scene_num: int,
    script_title: str = "",
    used_sources: Optional[set] = None,
) -> str:
    clean_ai_prompt = _clean_visual_prompt(prompt, narration, script_title)
    keywords = _extract_search_keywords(prompt, narration, script_title)

    if await _generate_agnes_ai_image(clean_ai_prompt, output_path):
        return output_path

    if await _fetch_openverse_image(keywords, output_path, scene_num, used_sources=used_sources):
        return output_path

    if script_title and script_title != keywords:
        title_kw = _extract_search_keywords(script_title, "")
        if title_kw and await _fetch_openverse_image(title_kw, output_path, scene_num, used_sources=used_sources):
            return output_path

    if await _fetch_wikimedia_image(keywords, output_path, used_sources=used_sources):
        return output_path

    # Topic-aware stock fallback
    combined_text = f"{prompt} {narration} {script_title}".lower()
    if any(w in combined_text for w in ["car", "vehicle", "ferrari", "race", "motor"]):
        topic_key = "cars"
    elif any(w in combined_text for w in ["tech", "ai", "robot", "software", "computer", "cyber"]):
        topic_key = "tech"
    elif any(w in combined_text for w in ["business", "money", "finance", "invest"]):
        topic_key = "business"
    elif any(w in combined_text for w in ["gym", "workout", "fitness", "muscle"]):
        topic_key = "fitness"
    elif any(w in combined_text for w in ["food", "diet", "cook", "eat"]):
        topic_key = "food"
    elif any(w in combined_text for w in ["travel", "city", "beach", "hotel"]):
        topic_key = "travel"
    else:
        topic_key = "general"

    photo_urls = FALLBACK_PHOTO_TOPICS.get(topic_key, FALLBACK_PHOTO_TOPICS["general"])
    if used_sources is not None:
        available_photos = [u for u in photo_urls if u not in used_sources]
        fallback_url = available_photos[0] if available_photos else photo_urls[(scene_num - 1) % len(photo_urls)]
    else:
        fallback_url = photo_urls[(scene_num - 1) % len(photo_urls)]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(fallback_url, follow_redirects=True)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                _ensure_1080p(output_path)
                if used_sources is not None:
                    used_sources.add(fallback_url)
                return output_path
    except Exception as e:
        logger.warning(f"Stock photo fallback failed: {e}")

    _create_local_canvas(output_path)
    return output_path


def _ensure_1080p(image_path: str):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img.save(image_path, "JPEG", quality=92)
    except Exception:
        pass


def _create_local_canvas(output_path: str):
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1920, 16], fill=(59, 130, 246))
    draw.rectangle([0, 1064, 1920, 1080], fill=(59, 130, 246))
    img.save(output_path, "JPEG", quality=90)


# ─────────────────────────────────────────────────────────────────────────────
# CONCAT + FINAL ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def concat_scene_clips(clip_paths: List[str], final_output: str, ffmpeg_exe: str, aspect_ratio: str = "9:16") -> bool:
    """Concatenate all scene clips into a unified final video."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copyfile(clip_paths[0], final_output)
        return True

    tw, th = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    inputs = []
    filter_parts = []
    for i, p in enumerate(clip_paths):
        inputs.extend(["-i", p])
        # Normalize each input to matching resolution, pad if needed
        filter_parts.append(
            f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
        )

    # Build audio normalization
    audio_parts = []
    for i in range(len(clip_paths)):
        filter_parts.append(f"[{i}:a]aresample=44100[a{i}];")
        audio_parts.append(f"[v{i}][a{i}]")

    concat_in = "".join(audio_parts)
    filter_parts.append(f"{concat_in}concat=n={len(clip_paths)}:v=1:a=1[vout][aout]")
    filter_complex = "".join(filter_parts)

    cmd = [
        ffmpeg_exe, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        final_output,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        logger.info(f"Concatenated {len(clip_paths)} clips → {final_output}")
        return True

    logger.error(f"Filter complex concat failed: {res.stderr[:300]}")

    # Simple fallback concat without normalization
    inputs2 = []
    filter_parts2 = []
    for i, p in enumerate(clip_paths):
        inputs2.extend(["-i", p])
        filter_parts2.append(f"[{i}:v][{i}:a]")
    filter_complex2 = "".join(filter_parts2) + f"concat=n={len(clip_paths)}:v=1:a=1[v][a]"
    cmd2 = [
        ffmpeg_exe, "-y",
        *inputs2,
        "-filter_complex", filter_complex2,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        final_output,
    ]
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    return res2.returncode == 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def generate_free_video(
    task_id: str,
    project_id: str,
    script: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], Any]] = None,
    aspect_ratio: str = "9:16",
) -> Tuple[str, str, int]:
    """Generate a complete multi-scene animated video.

    For each scene:
      - Renders a procedural motion graphic animation (concept-driven)
      - Falls back to photo + Ken Burns only if animation fails

    Returns:
        (cloudinary_url, cloudinary_public_id, duration_seconds)
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = script.get("scenes") or []
    if not scenes:
        scenes = [{
            "scene_number": 1,
            "narration": script.get("hook") or script.get("title") or "Video overview.",
            "visual_description": script.get("title") or "Cinematic overview",
            "duration_seconds": 5,
        }]

    voice = _get_voice_for_tone(script.get("tone", "professional"))
    script_title = str(script.get("title") or "")

    animated_count = 0
    photo_count = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        clip_paths: List[str] = []
        total_scenes = len(scenes)
        total_duration = 0.0
        used_sources: set = set()

        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            narration = scene.get("narration", "")
            visual = scene.get("visual_description", "")

            pct = int(10 + (i / total_scenes) * 70)
            if progress_callback:
                await progress_callback(pct, f"Rendering Scene {scene_num}/{total_scenes}")

            # ── Step 1: Generate audio + SRT ────────────────────────────────
            audio_file = os.path.join(tmp_dir, f"audio_{scene_num}.mp3")
            srt_file = os.path.join(tmp_dir, f"sub_{scene_num}.srt")
            has_audio, audio_duration = await generate_scene_audio_and_subtitles(
                text=narration,
                audio_path=audio_file,
                srt_path=srt_file,
                voice=voice,
            )
            total_duration += audio_duration

            clip_file = os.path.join(tmp_dir, f"clip_{scene_num}.mp4")

            # ── Step 2: Attempt animation-first rendering ────────────────────
            concept_key = detect_concept_key(scene, topic=script_title)

            if concept_key:
                logger.info(f"[Scene {scene_num}] Animation path: concept_key='{concept_key}'")
                anim_ok = render_animated_scene_clip(
                    concept_key=concept_key,
                    audio_path=audio_file if has_audio else None,
                    srt_path=srt_file if has_audio else None,
                    output_path=clip_file,
                    ffmpeg_exe=ffmpeg_exe,
                    duration=audio_duration,
                    scene_num=scene_num,
                    title=script_title or narration[:40],
                    narration=narration,
                    scene_metadata=scene,
                    aspect_ratio=aspect_ratio,
                )
                if anim_ok and os.path.exists(clip_file):
                    clip_paths.append(clip_file)
                    animated_count += 1
                    logger.info(f"[Scene {scene_num}] ✅ Animated clip rendered ({concept_key})")
                    continue  # skip photo fallback

                logger.warning(f"[Scene {scene_num}] Animation failed for '{concept_key}', falling back to photo.")

            # ── Step 3: Photo fallback ───────────────────────────────────────
            logger.info(f"[Scene {scene_num}] Photo path (no concept or anim failed)")
            image_file = os.path.join(tmp_dir, f"image_{scene_num}.jpg")
            await fetch_scene_image(
                prompt=visual,
                narration=narration,
                output_path=image_file,
                scene_num=scene_num,
                script_title=script_title,
                used_sources=used_sources,
            )

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
                photo_count += 1

        if not clip_paths:
            raise RuntimeError("Failed to render any scene clips")

        logger.info(
            f"[Task {task_id}] Scene summary: {animated_count} animated, "
            f"{photo_count} photo-based, {total_scenes} total"
        )

        # ── Step 4: Assemble final video ─────────────────────────────────────
        if progress_callback:
            await progress_callback(85, f"Assembling {len(clip_paths)} scenes into final video...")

        final_mp4 = os.path.join(tmp_dir, "final_video.mp4")
        concat_scene_clips(clip_paths, final_mp4, ffmpeg_exe, aspect_ratio=aspect_ratio)

        # ── Step 5: Upload to Cloudinary ─────────────────────────────────────
        if progress_callback:
            await progress_callback(93, "Uploading to Cloudinary...")

        cloudinary_url, cloudinary_public_id = await upload_video_file(
            file_path=final_mp4,
            project_id=project_id,
            task_id=task_id,
        )

        final_duration_sec = int(total_duration or len(scenes) * 5)
        logger.info(f"[Task {task_id}] Video complete: {animated_count}/{total_scenes} scenes animated. URL: {cloudinary_url}")
        return cloudinary_url, cloudinary_public_id, final_duration_sec


async def sync_audio_and_captions_to_video(
    video_url: str,
    script: Dict[str, Any],
    task_id: str,
    project_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Add neural voiceover and burned captions to a raw video (e.g. from Agnes AI)."""
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
            text=narration, audio_path=audio_file, srt_path=srt_file, voice=voice,
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
