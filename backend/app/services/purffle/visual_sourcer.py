"""Visual sourcing service for PurffleShorts.

Fetches and formats high-fidelity vertical (1080x1920) imagery from NASA Images API,
Wikimedia Commons, and Pollinations AI with smart 9:16 cropping and framing.
"""

import asyncio
import io
import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFilter

from app.services.purffle.motion_graphics import detect_concept_key, render_motion_graphic_clip

logger = logging.getLogger(__name__)

USER_AGENT = "QreateEducational/2.0 (video-generation; contact@qreate.local)"


def _crop_to_vertical_1080x1920(image_bytes: bytes, dest_path: str) -> bool:
    """Crop and resize any source image to true 1080x1920 (9:16) portrait format."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            w, h = img.size

            target_ratio = 9.0 / 16.0
            current_ratio = w / float(h)

            if current_ratio > target_ratio:
                # Source is wider than 9:16 -> crop left and right
                new_w = int(h * target_ratio)
                left = max(0, (w - new_w) // 2)
                img_cropped = img.crop((left, 0, left + new_w, h))
            else:
                # Source is taller than 9:16 -> crop top and bottom
                new_h = int(w / target_ratio)
                top = max(0, (h - new_h) // 2)
                img_cropped = img.crop((0, top, w, top + new_h))

            # Resize to full HD 1080x1920
            final_img = img_cropped.resize((1080, 1920), Image.Resampling.LANCZOS)
            final_img.save(dest_path, "JPEG", quality=95, optimize=True)
            return True
    except Exception as e:
        logger.warning(f"Error processing image for {dest_path}: {e}")
        return False


def _create_fallback_canvas(dest_path: str, title: str, subtitle: str):
    """Create a sleek, high-contrast dark space/science canvas if network assets are unavailable."""
    try:
        img = Image.new("RGB", (1080, 1920), color=(10, 12, 22))
        draw = ImageDraw.Draw(img)

        # Draw deep space radial glow
        center_x, center_y = 540, 960
        for r in range(480, 50, -30):
            alpha = int(25 * (1 - r / 480))
            draw.ellipse(
                [center_x - r, center_y - r, center_x + r, center_y + r],
                fill=(18 + alpha, 22 + alpha, 40 + alpha * 2),
            )

        img = img.filter(ImageFilter.GaussianBlur(radius=8))
        img.save(dest_path, "JPEG", quality=90)
    except Exception as e:
        logger.error(f"Fallback canvas creation failed: {e}")


async def _search_nasa_images(client: httpx.AsyncClient, query: str) -> List[str]:
    """Search NASA Image and Video Library for public domain scientific/astronomical photography."""
    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    if not clean_q:
        return []
    url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(clean_q)}&media_type=image"
    try:
        resp = await client.get(url, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("collection", {}).get("items", [])
            urls = []
            for it in items[:6]:
                links = it.get("links", [])
                for l in links:
                    href = l.get("href", "")
                    if href and href.endswith((".jpg", ".png", ".jpeg")):
                        # Prefer large/orig image URL if available
                        large_href = href.replace("~thumb.", "~medium.").replace("~small.", "~medium.")
                        urls.append(large_href)
                        break
            return urls
    except Exception as e:
        logger.debug(f"NASA image search failed for '{query}': {e}")
    return []


async def _search_wikimedia_commons(client: httpx.AsyncClient, query: str) -> List[str]:
    """Search Wikimedia Commons for open educational diagrams and scientific figures."""
    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    if not clean_q:
        return []
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrsearch={urllib.parse.quote(clean_q)}&gsrnamespace=6&prop=imageinfo&iiprop=url|size&format=json"
    )
    try:
        resp = await client.get(url, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            urls = []
            for p in pages.values():
                info = p.get("imageinfo", [{}])[0]
                img_url = info.get("url", "")
                if img_url and img_url.lower().endswith((".jpg", ".png", ".jpeg")):
                    urls.append(img_url)
            return urls
    except Exception as e:
        logger.debug(f"Wikimedia search failed for '{query}': {e}")
    return []


async def _fetch_pollinations_image(client: httpx.AsyncClient, prompt: str, seed: int) -> Optional[bytes]:
    """Generate a conceptual vertical 1080x1920 image via Pollinations AI."""
    enhanced_prompt = f"{prompt}, 8k resolution, cinematic lighting, vertical 9:16 composition, highly detailed"
    encoded = urllib.parse.quote(enhanced_prompt[:400])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={seed}"
    try:
        resp = await client.get(url, timeout=14.0, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 5000:
            return resp.content
    except Exception as e:
        logger.debug(f"Pollinations fetch failed: {e}")
    return None


SCENE_TOKENS = [
    "sceneone", "scenetwo", "scenethree", "scenefour", "scenefive",
    "scenesix", "sceneseven", "sceneeight", "scenenine", "sceneten",
    "sceneeleven", "scenetwelve", "scenethirteen", "scenefourteen", "scenefifteen",
    "scenesixteen", "sceneseventeen", "sceneeighteen", "scenenineteen", "scenetwenty",
]


async def source_visuals_for_scenes(
    scenes: List[Dict[str, Any]],
    topic: str,
    output_media_dir: str,
) -> List[Tuple[str, str]]:
    """Download, format, and save 1080x1920 portrait visuals for each scene into output_media_dir.

    Renders dynamic explanatory motion graphics for physics/process/movement scenes,
    and sources high-res photography (NASA, Wikimedia, Pollinations) for hero and evidence scenes.

    Returns a list of (search_query_keyword, filepath) for each scene.
    """
    os.makedirs(output_media_dir, exist_ok=True)
    results: List[Tuple[str, str]] = []

    is_space_or_physics = any(
        w in (topic.lower()) for w in ["space", "black hole", "light", "gravity", "physics", "universe", "star", "galaxy", "quantum", "relativity"]
    )

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=12.0) as client:
        for idx, sc in enumerate(scenes, 1):
            subject = str(sc.get("visual_subject") or "").strip()
            desc = str(sc.get("visual_description") or "").strip()
            action = str(sc.get("visual_action") or "").strip()
            narration = str(sc.get("narration") or "").strip()
            v_type = str(sc.get("visual_type") or "").strip()

            # Assign unique phonetic token for deterministic 1:1 timeline matching
            token = SCENE_TOKENS[idx - 1] if idx - 1 < len(SCENE_TOKENS) else f"scene{idx}"

            # Formulate 2-4 clean keywords
            candidate_text = f"{subject} {action}".strip() or desc or narration
            words = [re.sub(r"[^\w]", "", w).lower() for w in candidate_text.split() if len(w) > 3][:4]
            keyword_stem = "_".join(words) if words else f"scene_{idx}"
            search_phrase = f"{token} {' '.join(words) if words else topic[:25]}".strip()

            # ── V3 MOTION GRAPHICS GENERATION ────────────────────────────
            # Check if this scene calls for an explanatory motion graphic
            concept_key = detect_concept_key(sc, topic)
            if concept_key:
                anim_filename = f"scene_{idx:02d}_{token}_{keyword_stem}.mp4"
                anim_dest = os.path.join(output_media_dir, anim_filename)
                duration = float(sc.get("duration_seconds") or 4.0)

                try:
                    ok = await asyncio.to_thread(
                        render_motion_graphic_clip,
                        concept_key=concept_key,
                        output_mp4_path=anim_dest,
                        duration_seconds=duration,
                        title=topic,
                        narration=narration,
                        scene_metadata=sc,
                    )
                    if ok and os.path.isfile(anim_dest) and os.path.getsize(anim_dest) > 1000:
                        logger.info(f"Scene {idx}: Rendered V3 animated diagram ({concept_key}) -> {anim_filename}")
                        results.append((search_phrase, anim_dest))
                        continue
                    else:
                        logger.warning(f"Scene {idx}: Animation failed for {concept_key}; falling back to sourced photo.")
                except Exception as anim_err:
                    logger.warning(f"Scene {idx}: Motion graphics exception: {anim_err}; falling back to sourced photo.")

            # ── PHOTOGRAPHIC / DIAGRAM SOURCING (HERO & EVIDENCE) ────────
            img_filename = f"scene_{idx:02d}_{token}_{keyword_stem}.jpg"
            dest_file = os.path.join(output_media_dir, img_filename)
            downloaded = False

            # 1. Try NASA Images for space/astrophysics
            if is_space_or_physics:
                nasa_queries = [" ".join(words) if words else "", subject, topic]
                for nq in nasa_queries:
                    if not nq:
                        continue
                    urls = await _search_nasa_images(client, nq)
                    for u in urls:
                        try:
                            r = await client.get(u, timeout=8.0)
                            if r.status_code == 200 and len(r.content) > 10000:
                                if _crop_to_vertical_1080x1920(r.content, dest_file):
                                    downloaded = True
                                    logger.info(f"Scene {idx}: Sourced NASA visual for '{search_phrase}' -> {img_filename}")
                                    break
                        except Exception:
                            continue
                    if downloaded:
                        break

            # 2. Try Wikimedia Commons for diagrams
            if not downloaded:
                wiki_urls = await _search_wikimedia_commons(client, " ".join(words) if words else topic)
                for wu in wiki_urls:
                    try:
                        r = await client.get(wu, timeout=8.0)
                        if r.status_code == 200 and len(r.content) > 10000:
                            if _crop_to_vertical_1080x1920(r.content, dest_file):
                                downloaded = True
                                logger.info(f"Scene {idx}: Sourced Wikimedia visual for '{search_phrase}' -> {img_filename}")
                                break
                    except Exception:
                        continue

            # 3. Try Pollinations AI
            if not downloaded:
                ai_prompt = f"{desc or subject or topic}, cinematic 35mm film photography, 8k, photorealistic"
                ai_bytes = await _fetch_pollinations_image(client, ai_prompt, seed=idx * 231 + 17)
                if ai_bytes and _crop_to_vertical_1080x1920(ai_bytes, dest_file):
                    downloaded = True
                    logger.info(f"Scene {idx}: Sourced AI visual for '{search_phrase}' -> {img_filename}")

            # 4. Fallback procedural canvas
            if not downloaded or not os.path.isfile(dest_file):
                _create_fallback_canvas(dest_file, title=topic, subtitle=subject or f"Scene {idx}")
                logger.info(f"Scene {idx}: Created fallback canvas -> {img_filename}")

            results.append((search_phrase, dest_file))

    return results
