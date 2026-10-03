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
    TRANSITION, SceneRender, compose_final, make_text_card, render_scene, render_scenes_parallel,
)
from app.services.media.music import fetch_music
from app.services.media.stock import PLACES, MediaAsset, StockContext, fetch_user_media, find_scene_media
from app.services.media.tts import pick_voice, synthesize_script

logger = logging.getLogger(__name__)

Reporter = Callable[[int, str], Awaitable[None]]

FINAL_TAIL = 0.9      # let the last shot land after the last word
MIN_SCENE = 1.2


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


def _fill_with_cards(assets: List[Optional[MediaAsset]], scenes: List[Dict], work: str) -> List[MediaAsset]:
    """Replace scenes without relevant footage by text cards over a neighbouring real photo."""
    out: List[MediaAsset] = []
    for i, a in enumerate(assets):
        if a is not None:
            out.append(a)
            continue
        neighbour = next(
            (n.path for n in (assets[i - 1:i] + assets[i + 1:i + 2] + assets) if n is not None and n.kind == "image"),
            None,
        )
        scene = scenes[i] if i < len(scenes) else {}
        text = scene.get("on_screen_text") or ""
        path = make_text_card(text, os.path.join(work, f"card_{i}.jpg"), background=neighbour, seed=i)
        out.append(MediaAsset("image", path, "card", f"card_{i}"))
    return out


async def produce_video(script: Dict[str, Any], job_id: str, project_id: str, report: Reporter) -> Dict[str, Any]:
    """Render `script` into a finished vertical MP4 and upload it. Returns result metadata."""
    s = get_settings()
    timings: Dict[str, float] = {}
    t0 = time.monotonic()
    scenes = script.get("scenes") or [{}]
    lines = _narration_lines(script)
    language = script.get("language", "English")
    voice = pick_voice(language, script.get("tone", ""), script.get("voice_gender", "male"))
    latin = language.lower() not in ("hindi", "japanese", "chinese")
    user_media = script.get("user_media") or []

    with tempfile.TemporaryDirectory(prefix=f"qreate_{job_id}_") as work:
        # ── 1. One-take voiceover + music + creator media (concurrently) ─────
        await report(20, "voiceover")
        music_task = (
            fetch_music(script.get("music_mood", "cinematic"), os.path.join(work, "music.mp3"))
            if s.ENABLE_MUSIC else asyncio.sleep(0, result=None)
        )
        narration, music_path, own_assets = await asyncio.gather(
            synthesize_script(lines, os.path.join(work, "voice.mp3"), voice, script.get("tone", "")),
            music_task,
            fetch_user_media(user_media, os.path.join(work, "user")),
        )
        durations = _scene_durations(narration.scene_starts, narration.duration)
        timings["voice"] = time.monotonic() - t0

        # ── 2. Visuals ──────────────────────────────────────────────────────
        await report(35, "finding footage")
        ctx = StockContext()
        if own_assets:
            # Personal story: the creator's media, spread across every scene
            assets: List[Optional[MediaAsset]] = [own_assets[i % len(own_assets)] for i in range(len(lines))]
        else:
            assets = await _gather_limited(
                [
                    find_scene_media(
                        _queries_for(scenes[i] if i < len(scenes) else {}),
                        min_duration=durations[i] + TRANSITION,
                        dest_base=os.path.join(work, f"media_{i}"),
                        ctx=ctx,
                        description=_visual_brief(scenes[i] if i < len(scenes) else {}, script),
                    )
                    for i in range(len(lines))
                ],
                limit=3,
            )
        assets = _fill_with_cards(assets, scenes, work)
        timings["footage"] = time.monotonic() - t0

        # ── 3. Scene renders ────────────────────────────────────────────────
        await report(50, "rendering scenes")
        scene_paths = await render_scenes_parallel(
            [
                render_scene(
                    asset,
                    durations[i] + (TRANSITION if i < len(lines) - 1 else 0.0),
                    os.path.join(work, f"scene_{i}.mp4"),
                    i, work,
                )
                for i, asset in enumerate(assets)
            ],
            limit=s.SCENE_RENDER_PARALLELISM,
        )
        timings["scenes"] = time.monotonic() - t0

        # ── 4. Captions ─────────────────────────────────────────────────────
        await report(75, "captions & audio")
        ass_path = os.path.join(work, "captions.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(captions_mod.build_ass(
                narration.words, s.VIDEO_WIDTH, s.VIDEO_HEIGHT,
                hook_text=script.get("hook_text") or None,
                hook_end=min(durations[0], 3.2),
                uppercase=latin,
            ))

        # ── 5. Final edit ───────────────────────────────────────────────────
        await report(82, "final edit")
        final_path = os.path.join(work, "final.mp4")
        total = await compose_final(
            [SceneRender(p, d) for p, d in zip(scene_paths, durations)],
            narration.audio_path, ass_path, final_path, music_path,
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
        "music": bool(music_path),
        "credits": ctx.credits,
        "voice": voice,
        "timings": {k: round(v, 1) for k, v in timings.items()},
    }
