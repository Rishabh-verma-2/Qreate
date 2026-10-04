"""End-to-end pipeline: script → one-take voiceover → visuals → edit → captions → upload.

Visual priority per scene:
  1. The creator's own uploaded photos/videos (personal stories look real because they are)
  2. Relevant real stock footage / photos
  3. A bold text card over a blurred neighbouring shot (never an unrelated picture)
"""

import asyncio
import logging
import os
import tempfile
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.config import get_settings
from app.services.cloudinary.uploader import upload_video_file
from app.services.media import captions as captions_mod
from app.services.media.composer import (
    SceneRender, compose_final, make_text_card, render_scene, render_scenes_parallel,
)
from app.services.media.music import detect_beats, fetch_music
from app.services.media.stock import PLACES, MediaAsset, StockContext, fetch_user_media, find_scene_media
from app.services.media import voices as voice_catalog
from app.services.media.themes import get_theme
from app.services.media.tts import pick_voice, synthesize_script

logger = logging.getLogger(__name__)

Reporter = Callable[[int, str], Awaitable[None]]

FINAL_TAIL = 0.9      # let the last shot land after the last word
MIN_SCENE = 1.2
SHOT_TARGET = 2.1     # real reels cut roughly every 1.5–2.5 s
PACE = {  # pace → (seconds per shot, voice rate)
    "fast": (1.7, "+10%"),
    "normal": (2.3, "+4%"),
    "calm": (3.0, "-3%"),
}
MIN_SHOT = 1.0
BEAT_SNAP = 0.18      # move an in-scene cut onto a music beat if one is this close


def _narration_lines(script: Dict[str, Any]) -> List[str]:
    scenes = script.get("scenes") or []
    lines = [str(s.get("narration") or "").strip() for s in scenes]
    hook, closing = (script.get("hook") or "").strip(), (script.get("closing") or "").strip()
    if not lines:
        lines = [hook or script.get("title") or "..."]
    if hook and not lines[0].lower().startswith(hook.lower()[:20]):
        lines[0] = f"{hook} {lines[0]}".strip()
    if closing and closing.lower()[:20] not in lines[-1].lower():
        lines[-1] = f"{lines[-1]} {closing}".strip()
    return lines


def _queries_for(scene: Dict[str, Any]) -> List[str]:
    qs = [q.strip() for q in (scene.get("search_queries") or []) if isinstance(q, str) and q.strip()]
    if not qs and scene.get("visual_description"):
        qs = [" ".join(scene["visual_description"].split()[:4])]
    # Relaxed variants (the last two words usually carry the subject: "...wedding dance")
    relaxed = []
    for q in qs:
        words = q.split()
        if len(words) > 2:
            place = [w for w in words[:-2] if PLACES.search(w.lower())]
            relaxed.append(" ".join(place + words[-2:]))
    return list(dict.fromkeys(qs + relaxed))


def _visual_brief(scene: Dict[str, Any], script: Dict[str, Any]) -> str:
    """Text CLIP compares thumbnails against: what the viewer should see."""
    desc = (scene.get("visual_description") or "").strip()
    if not desc:
        desc = ", ".join(scene.get("search_queries") or []) or script.get("title", "")
    return desc[:300]


def _scene_durations(starts: List[float], audio_duration: float) -> List[float]:
    ends = starts[1:] + [audio_duration + FINAL_TAIL]
    return [max(e - s, MIN_SCENE) for s, e in zip(starts, ends)]


async def _gather_limited(coros, limit: int):
    sem = asyncio.Semaphore(limit)

    async def run(c):
        async with sem:
            return await c

    return await asyncio.gather(*(run(c) for c in coros))


def _shots_for_scene(duration: float, target: float = SHOT_TARGET) -> int:
    return max(1, min(4, round(duration / target))) if duration >= 2 * MIN_SHOT + 0.4 else 1


def _split(start: float, duration: float, n: int, beats: List[float]) -> List[float]:
    """Split a scene into n shot lengths, snapping inner cuts to nearby beats."""
    cuts = [start + duration * k / n for k in range(1, n)]
    snapped = []
    for c in cuts:
        near = min(beats, key=lambda b: abs(b - c)) if beats else None
        snapped.append(near if near is not None and abs(near - c) <= BEAT_SNAP else c)
    bounds = [start] + snapped + [start + duration]
    lengths = [max(b - a, MIN_SHOT) for a, b in zip(bounds, bounds[1:])]
    scale = duration / sum(lengths)  # keep the scene length exact
    return [l * scale for l in lengths]


def _card(scenes: List[Dict], i: int, neighbour: Optional[str], work: str, theme=None) -> MediaAsset:
    scene = scenes[i] if i < len(scenes) else {}
    path = make_text_card(scene.get("on_screen_text") or "", os.path.join(work, f"card_{i}.jpg"),
                          background=neighbour, seed=i, theme=theme)
    return MediaAsset("image", path, "card", f"card_{i}")


async def produce_video(script: Dict[str, Any], job_id: str, project_id: str, report: Reporter) -> Dict[str, Any]:
    """Render `script` into a finished vertical MP4 and upload it. Returns result metadata."""
    s = get_settings()
    timings: Dict[str, float] = {}
    t0 = time.monotonic()
    scenes = script.get("scenes") or [{}]
    lines = _narration_lines(script)
    language = script.get("language", "English")
    style = script.get("style") or {}
    gender = style.get("voice_gender") or script.get("voice_gender", "male")
    if voice_catalog.is_valid_voice(style.get("voice_id")):
        voice = style["voice_id"]
    else:
        voice = (voice_catalog.default_voice(language, gender) if language not in ("English", "Hinglish", "Hindi")
                 else None) or pick_voice(language, script.get("tone", ""), gender)
    latin = language in voice_catalog.LATIN_LANGUAGES
    theme = get_theme(style.get("color_theme"), style.get("accent_color"))
    shot_target, voice_rate = PACE.get(style.get("pace") or "fast", PACE["fast"])
    mood = style.get("music_mood") or "auto"
    mood = script.get("music_mood", "cinematic") if mood == "auto" else mood
    user_media = script.get("user_media") or []

    with tempfile.TemporaryDirectory(prefix=f"qreate_{job_id}_") as work:
        # ── 1. One-take voiceover + music + creator media (concurrently) ─────
        await report(20, "voiceover")

        async def _voice_progress(ratio: float):
            pct = int(20 + ratio * 12)  # 20% to 32%
            await report(pct, "voiceover")

        music_task = (
            fetch_music(mood, os.path.join(work, "music.mp3"), timeout_seconds=5.0)
            if s.ENABLE_MUSIC and mood != "none" else asyncio.sleep(0, result=None)
        )
        narration, music_path, own_assets = await asyncio.gather(
            synthesize_script(
                lines, os.path.join(work, "voice.mp3"), voice,
                script.get("tone", ""), rate=voice_rate, on_progress=_voice_progress
            ),
            music_task,
            fetch_user_media(user_media, os.path.join(work, "user")),
        )
        # Keep the reel near its target length: long-word languages (Tamil, Malayalam…)
        # overshoot word budgets, so re-voice faster (max +25%) instead of running long.
        target = float(script.get("duration_seconds") or 30)
        if narration.duration > target * 1.3:
            current = int(voice_rate.rstrip("%"))
            faster = min(25, current + int((narration.duration / (target * 1.15) - 1) * 100))
            if faster > current:
                logger.info(f"[{job_id}] voiceover {narration.duration:.1f}s vs target {target:.0f}s → re-voicing at +{faster}%")
                narration = await synthesize_script(lines, os.path.join(work, "voice_fast.mp3"), voice,
                                                    script.get("tone", ""), rate=f"+{faster}%")
        durations = _scene_durations(narration.scene_starts, narration.duration)
        timings["voice"] = time.monotonic() - t0

        await report(33, "syncing audio & beats")
        beats = await detect_beats(music_path) if music_path else []

        # ── 2. Visuals: several matching shots per scene ────────────────────
        await report(35, "finding footage")
        shot_counts = [_shots_for_scene(d, shot_target) for d in durations]
        ctx = StockContext(visual_style=style.get("visual_style") or "real",
                           people_focus=style.get("people_focus", True) is not False)
        if own_assets:
            # Personal story: walk through the creator's media in order, one per shot
            per_scene, k = [], 0
            for n in shot_counts:
                per_scene.append([own_assets[(k + j) % len(own_assets)] for j in range(n)])
                k += n
        else:
            total_scenes = len(lines)
            completed_scenes = 0

            async def _find_scene_with_progress(i: int):
                nonlocal completed_scenes
                res = await find_scene_media(
                    _queries_for(scenes[i] if i < len(scenes) else {}),
                    min_duration=durations[i] / shot_counts[i],
                    dest_base=os.path.join(work, f"media_{i}"),
                    ctx=ctx,
                    description=_visual_brief(scenes[i] if i < len(scenes) else {}, script),
                    max_assets=shot_counts[i],
                )
                completed_scenes += 1
                pct = int(35 + (completed_scenes / max(total_scenes, 1)) * 14)
                await report(pct, f"finding footage ({completed_scenes}/{total_scenes})")
                return res

            per_scene = await _gather_limited(
                [_find_scene_with_progress(i) for i in range(total_scenes)],
                limit=3,
            )
        timings["footage"] = time.monotonic() - t0

        # ── 3. Shot plan + renders ──────────────────────────────────────────
        await report(50, "editing shots")
        plan = []  # (asset, duration, variant)
        all_images = [a.path for sc in per_scene for a in sc if a.kind == "image"]
        for i, (assets_i, n) in enumerate(zip(per_scene, shot_counts)):
            if not assets_i:
                assets_i, n = [_card(scenes, i, all_images[0] if all_images else None, work, theme)], 1
            for j, length in enumerate(_split(narration.scene_starts[i], durations[i], n, beats)):
                plan.append((assets_i[j % len(assets_i)], length, j // len(assets_i)))

        total_shots = len(plan)
        completed_shots = 0

        async def _render_shot_with_progress(k, asset, length, variant):
            nonlocal completed_shots
            res = await render_scene(
                asset, length, os.path.join(work, f"shot_{k}.mp4"), k, work,
                variant=variant, grade=theme.grade
            )
            completed_shots += 1
            pct = int(50 + (completed_shots / max(total_shots, 1)) * 24)
            await report(pct, f"editing shots ({completed_shots}/{total_shots})")
            return res

        shot_paths = await render_scenes_parallel(
            [
                _render_shot_with_progress(k, asset, length, variant)
                for k, (asset, length, variant) in enumerate(plan)
            ],
            limit=s.SCENE_RENDER_PARALLELISM,
        )
        timings["scenes"] = time.monotonic() - t0
        assets = [a for a, _, _ in plan]

        # ── 4. Captions ─────────────────────────────────────────────────────
        await report(75, "captions & audio")
        ass_path = os.path.join(work, "captions.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(captions_mod.build_ass(
                narration.words, s.VIDEO_WIDTH, s.VIDEO_HEIGHT,
                hook_text=script.get("hook_text") or None,
                hook_end=min(durations[0], 3.2),
                uppercase=latin,
                theme=theme,
                caption_style=style.get("caption_style") or "bold",
                language=language,
            ))

        # ── 5. Final edit ───────────────────────────────────────────────────
        await report(82, "final edit")
        final_path = os.path.join(work, "final.mp4")
        total = await compose_final(
            [SceneRender(p, d) for p, (_, d, _) in zip(shot_paths, plan)],
            narration.audio_path, ass_path, final_path, music_path,
            sfx_times=narration.scene_starts[1:],
        )
        timings["compose"] = time.monotonic() - t0
        size_mb = os.path.getsize(final_path) / 1e6

        # ── 6. Upload ───────────────────────────────────────────────────────
        await report(94, "uploading")
        url, public_id = await upload_video_file(final_path, project_id, job_id)
        timings["total"] = time.monotonic() - t0

    thumb = None
    if url and "/upload/" in url:
        thumb = url.replace("/upload/", "/upload/so_1.0,w_540/").rsplit(".", 1)[0] + ".jpg"

    logger.info(f"[{job_id}] video ready in {timings['total']:.1f}s ({total:.1f}s, {size_mb:.1f} MB): {url}")
    return {
        "cloudinary_url": url,
        "cloudinary_public_id": public_id,
        "thumbnail_url": thumb,
        "duration_seconds": round(total, 1),
        "file_size_mb": round(size_mb, 2),
        "width": s.VIDEO_WIDTH,
        "height": s.VIDEO_HEIGHT,
        "media_sources": [a.source for a in assets],
        "shots": len(plan),
        "music": bool(music_path),
        "credits": ctx.credits,
        "voice": voice,
        "style": style,
        "timings": {k: round(v, 1) for k, v in timings.items()},
    }
