"""Real-footage finder for each scene.

Order (first relevant hit wins):
  1. Pexels videos   (free API key, portrait HD footage)
  2. Pixabay videos  (free API key)
  3. Pexels photos   (free API key)
  4. Unsplash photos (free API key — highest-quality real photography)
  5. Pixabay photos  (free API key)
  6. Openverse modern stock photos (no key — StockSnap/Nappy, strict match)
If nothing relevant is found the caller renders a bold text card instead of an
unrelated picture. No AI-generated images are ever used.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.core.config import get_settings
from app.services.media.http import TTLCache, download, get_json

logger = logging.getLogger(__name__)

_search_cache = TTLCache()

_STOP = {"the", "and", "with", "for", "from", "into", "over", "your", "this", "that", "shot", "close",
         "closeup", "view", "slow", "motion", "footage", "video", "photo", "stock"}
# Motion graphics / cartoons / green screens look fake next to real footage
_NOT_REAL = re.compile(
    r"\b(animation|animated|cartoon|green ?screen|chroma|3d|render|rendering|cgi|illustration|vector|"
    r"motion graphics?|particles?|abstract|loop(?:able)?|intro|logo|subscribe|like button|emoji|"
    r"icon|infographic|clip ?art|anime|text|title|transition)\b",
    re.IGNORECASE,
)
# Old/archival look kills relatability for modern short-form
_ARCHIVAL = re.compile(
    r"\b(1[6-9]\d\d|historical|history of|vintage|archive|archival|museum|antique|engraving|illustration|"
    r"painting|drawing|black and white|monochrome|sepia|postcard|manuscript|diagram|map of|logo)\b",
    re.IGNORECASE,
)


@dataclass
class MediaAsset:
    kind: str                    # "video" | "image"
    path: str
    source: str
    asset_id: str
    duration: float = 0.0        # videos only
    credit: Optional[str] = None  # attribution line when the licence needs one
    relevance: float = 1.0


@dataclass
class StockContext:
    """Per-job state: avoids reusing the same clip twice in one video."""
    used_ids: Set[str] = field(default_factory=set)
    credits: List[str] = field(default_factory=list)


# Place words are non-negotiable: "mumbai skyline" must not return Dubai.
PLACES = re.compile(
    r"\b(india|indian|mumbai|delhi|bangalore|bengaluru|kolkata|chennai|hyderabad|pune|jaipur|goa|kerala|"
    r"varanasi|agra|punjab|rajasthan|himalaya|ladakh|kashmir|desi|bollywood)\b"
)


def relevance(query: str, text: str) -> float:
    """Share of the query's meaningful words that appear in a result's title/tags/slug."""
    terms = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in _STOP]
    if not terms:
        return 1.0
    hay = text.lower().replace("-", " ")
    score = sum(1 for t in terms if t in hay or t.rstrip("s") in hay) / len(terms)
    places = PLACES.findall(query.lower())
    if places and not any(p in hay or (p in ("india", "indian", "desi") and "india" in hay) for p in places):
        score *= 0.3
    return score


# ── Pexels ────────────────────────────────────────────────────────────────────

def _pick_pexels_file(files: List[Dict]) -> Optional[Dict]:
    """Prefer a portrait ~1080x1920 MP4; avoid needless 4K downloads."""
    mp4s = [f for f in files if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    if not mp4s:
        return None

    def score(f):
        w, h = f["width"], f["height"]
        short_side = min(w, h)
        return (h >= w, short_side >= 720, short_side <= 1440, -abs(short_side - 1080))

    return max(mp4s, key=score)


async def _pexels_videos(query: str, min_duration: float) -> List[Dict]:
    key = get_settings().PEXELS_API_KEY
    if not key:
        return []
    cache_key = f"pexels_v:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        data = await get_json(
            "https://api.pexels.com/videos/search",
            params={"query": query, "orientation": "portrait", "per_page": 15, "size": "medium"},
            headers={"Authorization": key},
        ) or {}
        _search_cache.set(cache_key, data)
    out = []
    for rank, v in enumerate(data.get("videos", [])):
        f = _pick_pexels_file(v.get("video_files", []))
        if not f:
            continue
        # The page slug describes the clip ("/video/woman-pouring-tea-123/")
        out.append({
            "id": f"pexels_v_{v['id']}", "url": f["link"], "duration": float(v.get("duration") or 0),
            "thumb": v.get("image"), "kind": "video", "source": "pexels",
            "relevance": relevance(query, v.get("url", "")), "rank": rank,
        })
    # Pexels' own ranking is good; prefer clips whose description matches and that are long enough
    out.sort(key=lambda c: (c["relevance"] < 0.5, c["duration"] < min_duration, c["rank"]))
    return out


async def _pexels_photos(query: str) -> List[Dict]:
    key = get_settings().PEXELS_API_KEY
    if not key:
        return []
    cache_key = f"pexels_p:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        data = await get_json(
            "https://api.pexels.com/v1/search",
            params={"query": query, "orientation": "portrait", "per_page": 15},
            headers={"Authorization": key},
        ) or {}
        _search_cache.set(cache_key, data)
    out = []
    for rank, p in enumerate(data.get("photos", [])):
        if not p.get("src"):
            continue
        out.append({"id": f"pexels_p_{p['id']}", "url": p["src"].get("large2x") or p["src"].get("original"),
                    "thumb": p["src"].get("medium"), "kind": "image", "source": "pexels",
                    "relevance": relevance(query, f"{p.get('alt', '')} {p.get('url', '')}"), "rank": rank})
    out.sort(key=lambda c: (c["relevance"] < 0.5, c["rank"]))
    return out


# ── Pixabay ───────────────────────────────────────────────────────────────────

async def _pixabay_videos(query: str, min_duration: float) -> List[Dict]:
    key = get_settings().PIXABAY_API_KEY
    if not key:
        return []
    cache_key = f"pixabay_v:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        data = await get_json(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": query[:100], "per_page": 15, "safesearch": "true"},
        ) or {}
        _search_cache.set(cache_key, data)
    out = []
    for rank, hit in enumerate(data.get("hits", [])):
        # Real camera footage only — Pixabay marks motion graphics as type "animation"
        if hit.get("type") not in (None, "film") or _NOT_REAL.search(hit.get("tags", "")):
            continue
        variants = hit.get("videos", {})
        f = variants.get("large") if (variants.get("large") or {}).get("url") else variants.get("medium")
        if f and f.get("url"):
            out.append({"id": f"pixabay_v_{hit['id']}", "url": f["url"], "duration": float(hit.get("duration") or 0),
                        "thumb": (variants.get("tiny") or f).get("thumbnail"), "kind": "video", "source": "pixabay",
                        "relevance": relevance(query, hit.get("tags", "")), "rank": rank})
    out = [c for c in out if c["relevance"] >= 0.5]
    out.sort(key=lambda c: (-c["relevance"], c["duration"] < min_duration, c["rank"]))
    return out


async def _pixabay_photos(query: str) -> List[Dict]:
    key = get_settings().PIXABAY_API_KEY
    if not key:
        return []
    cache_key = f"pixabay_p:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        data = await get_json(
            "https://pixabay.com/api/",
            params={"key": key, "q": query[:100], "image_type": "photo", "orientation": "vertical",
                    "per_page": 20, "safesearch": "true", "min_height": 1200},
        ) or {}
        _search_cache.set(cache_key, data)
    hits = [h for h in data.get("hits", []) if not _NOT_REAL.search(h.get("tags", ""))]
    out = [
        {"id": f"pixabay_p_{h['id']}", "url": h.get("largeImageURL"), "thumb": h.get("webformatURL"),
         "kind": "image", "source": "pixabay", "relevance": relevance(query, h.get("tags", "")), "rank": i}
        for i, h in enumerate(hits) if h.get("largeImageURL")
    ]
    out = [c for c in out if c["relevance"] >= 0.5]
    out.sort(key=lambda c: (-c["relevance"], c["rank"]))
    return out


# ── Unsplash ──────────────────────────────────────────────────────────────────

async def _unsplash_photos(query: str) -> List[Dict]:
    key = get_settings().UNSPLASH_ACCESS_KEY
    if not key:
        return []
    cache_key = f"unsplash:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        data = await get_json(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "orientation": "portrait", "per_page": 15, "content_filter": "high"},
            headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
        ) or {}
        _search_cache.set(cache_key, data)
    out = []
    for rank, p in enumerate(data.get("results", [])):
        urls = p.get("urls") or {}
        if not urls.get("raw"):
            continue
        text = f"{p.get('alt_description') or ''} {p.get('description') or ''} {(p.get('links') or {}).get('html', '')}"
        name = (p.get("user") or {}).get("name") or "Unsplash"
        out.append({
            "id": f"unsplash_{p['id']}",
            # 1440px-wide JPEG: plenty for a 1080x1920 frame with camera movement
            "url": f"{urls['raw']}&w=1440&fm=jpg&q=85&fit=max",
            "thumb": urls.get("small"), "kind": "image", "source": "unsplash",
            "relevance": relevance(query, text), "rank": rank,
            "credit": f"Photo by {name} on Unsplash",
            "download_location": (p.get("links") or {}).get("download_location"),
        })
    out.sort(key=lambda c: (c["relevance"] < 0.5, c["rank"]))
    return out


async def _unsplash_track_download(cand: Dict) -> None:
    """Unsplash API guideline: report a download when a photo is actually used."""
    loc, key = cand.get("download_location"), get_settings().UNSPLASH_ACCESS_KEY
    if loc and key:
        await get_json(loc, headers={"Authorization": f"Client-ID {key}"})


# ── Openverse (no key) ────────────────────────────────────────────────────────

async def _openverse_query(query: str, sources: Optional[str]) -> List[Dict]:
    cache_key = f"openverse:{sources}:{query}"
    data = _search_cache.get(cache_key)
    if data is None:
        params = {"q": query, "page_size": 20, "license_type": "commercial", "size": "large",
                  "category": "photograph", "mature": "false"}
        if sources:
            params["source"] = sources
        data = await get_json("https://api.openverse.org/v1/images/", params=params) or {}
        _search_cache.set(cache_key, data)
    out = []
    for r in data.get("results", []):
        w, h = r.get("width") or 0, r.get("height") or 0
        if w and h and min(w, h) < 900:
            continue
        tags = " ".join(t.get("name", "") for t in (r.get("tags") or []) if isinstance(t, dict))
        text = f"{r.get('title') or ''} {tags}"
        if _ARCHIVAL.search(text) and not _ARCHIVAL.search(query):
            continue
        rel = relevance(query, text)
        if rel < 0.5:
            continue
        credit = (f'"{r.get("title") or "Photo"}" by {r.get("creator") or "unknown"} '
                  f'({(r.get("license") or "").upper()} {r.get("license_version") or ""}) via {r.get("source")}')
        out.append({"id": f"ov_{r['id']}", "url": r["url"], "relevance": rel, "tall": h >= w,
                    "thumb": r.get("thumbnail"), "kind": "image", "source": "openverse",
                    "credit": credit if r.get("license") != "cc0" else None})
    out.sort(key=lambda c: (-c["relevance"], not c["tall"]))
    return out


async def _openverse_photos(query: str) -> List[Dict]:
    # Only modern stock-photography sources. The wider archive (museums, Wikimedia,
    # random Flickr) matches tags but not meaning — a text card is better than a vase.
    return [c for c in await _openverse_query(query, "stocksnap,nappy") if c["relevance"] >= 0.67]


# ── Public API ────────────────────────────────────────────────────────────────

def _normalise_image(path: str) -> bool:
    """Convert to RGB JPEG; reject unreadable, tiny or near-greyscale (archival) images."""
    try:
        with Image.open(path) as img:
            if min(img.size) < 600:
                return False
            img = ImageOps.exif_transpose(img).convert("RGB")
            # Black-and-white photos read as "old/archival" — skip them
            small = img.resize((64, 64)).convert("HSV")
            if sum(p[1] for p in small.getdata()) / (64 * 64) < 18:
                return False
            img.save(path, "JPEG", quality=93)
        return True
    except Exception:
        return False


def create_gradient_background(path: str, seed: int = 0) -> str:
    """Soft blurred gradient (used behind text cards / as an offline guarantee)."""
    s = get_settings()
    palettes = [((24, 32, 58), (88, 60, 140)), ((14, 48, 56), (40, 120, 110)), ((48, 20, 40), (150, 70, 60))]
    top, bottom = palettes[seed % len(palettes)]
    img = Image.new("RGB", (s.VIDEO_WIDTH, s.VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(s.VIDEO_HEIGHT):
        t = y / s.VIDEO_HEIGHT
        draw.line([(0, y), (s.VIDEO_WIDTH, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    img = img.filter(ImageFilter.GaussianBlur(6))
    img.save(path, "JPEG", quality=92)
    return path


_VIDEO_FINDERS = (_pexels_videos, _pixabay_videos)
_PHOTO_FINDERS = (_pexels_photos, _unsplash_photos, _pixabay_photos, _openverse_photos)
VIDEO_BONUS = 0.015   # motion beats a still at equal relevance


async def _download_asset(cand: Dict, dest_base: str, ctx: StockContext) -> Optional[MediaAsset]:
    if cand["kind"] == "video":
        path = f"{dest_base}.mp4"
        if await download(cand["url"], path, min_bytes=50_000):
            return MediaAsset("video", path, cand["source"], cand["id"], duration=cand.get("duration", 0),
                              relevance=cand.get("score", cand["relevance"]))
        return None
    path = f"{dest_base}.jpg"
    if await download(cand["url"], path) and _normalise_image(path):
        if cand.get("credit"):
            ctx.credits.append(cand["credit"])
        if cand["source"] == "unsplash":
            await _unsplash_track_download(cand)
        return MediaAsset("image", path, cand["source"], cand["id"], credit=cand.get("credit"),
                          relevance=cand.get("score", cand["relevance"]))
    return None


async def _find_by_vision(queries: List[str], description: str, min_duration: float,
                          dest_base: str, ctx: StockContext) -> Optional[MediaAsset]:
    """Pool candidates from every source, let CLIP pick the best-looking match."""
    import asyncio
    import os

    from app.services.media import vision

    searches = []
    for q in queries[:3]:
        searches += [f(q, min_duration) for f in _VIDEO_FINDERS] + [f(q) for f in _PHOTO_FINDERS]
    pool: Dict[str, Dict] = {}
    for results in await asyncio.gather(*searches):
        for c in results[:6]:
            if c.get("thumb") and c["id"] not in ctx.used_ids:
                pool.setdefault(c["id"], c)
    cands = list(pool.values())[:30]
    if not cands:
        return None

    thumb_dir = f"{dest_base}_thumbs"
    os.makedirs(thumb_dir, exist_ok=True)
    paths = [os.path.join(thumb_dir, f"{i}.jpg") for i in range(len(cands))]
    ok = await asyncio.gather(*(download(c["thumb"], p, min_bytes=2_000) for c, p in zip(cands, paths)))
    scores = await vision.score_images(description, [p if good else None for p, good in zip(paths, ok)])

    for c, sc in zip(cands, scores):
        c["score"] = sc + (VIDEO_BONUS if c["kind"] == "video" else 0.0)
        if c["kind"] == "video" and c.get("duration", 0) < min_duration:
            c["score"] -= 0.01  # will need looping
    cands.sort(key=lambda c: -c["score"])
    logger.info(f"Vision pick for {description[:60]!r}: " + ", ".join(
        f"{c['source']}:{c['kind'][0]}={c['score']:.3f}" for c in cands[:3]))

    min_score = get_settings().RERANK_MIN_SCORE
    for c in cands[:5]:
        if c["score"] < min_score or c["id"] in ctx.used_ids:
            continue
        ctx.used_ids.add(c["id"])  # claim before awaiting: scenes search concurrently
        asset = await _download_asset(c, dest_base, ctx)
        if asset:
            return asset
    return None


async def find_scene_media(
    queries: List[str],
    min_duration: float,
    dest_base: str,
    ctx: StockContext,
    description: str = "",
) -> Optional[MediaAsset]:
    """Find and download the most relevant real footage for a scene, or None."""
    from app.services.media import vision

    queries = [q for q in queries if q]
    if vision.available():
        return await _find_by_vision(queries, description or queries[0], min_duration, dest_base, ctx)

    # Tag-based fallback: videos first, then photos, first acceptable hit wins
    for finders, is_video in ((_VIDEO_FINDERS, True), (_PHOTO_FINDERS, False)):
        for q in queries:
            for finder in finders:
                results = await (finder(q, min_duration) if is_video else finder(q))
                for cand in results[:6]:
                    if cand["id"] in ctx.used_ids:
                        continue
                    ctx.used_ids.add(cand["id"])
                    asset = await _download_asset(cand, dest_base, ctx)
                    if asset:
                        return asset

    logger.info(f"No relevant stock media for {queries}")
    return None


async def fetch_user_media(items: List[Dict], dest_base: str) -> List[MediaAsset]:
    """Download the creator's own uploaded photos/videos (already hosted on Cloudinary)."""
    out = []
    for i, item in enumerate(items):
        url = item.get("url")
        if not url:
            continue
        is_video = item.get("kind") == "video" or re.search(r"\.(mp4|mov|webm|m4v)(\?|$)", url, re.I)
        path = f"{dest_base}_{i}.{'mp4' if is_video else 'jpg'}"
        if not await download(url, path, min_bytes=5_000):
            continue
        if not is_video:
            try:
                with Image.open(path) as img:
                    ImageOps.exif_transpose(img).convert("RGB").save(path, "JPEG", quality=94)
            except Exception:
                continue
        out.append(MediaAsset("video" if is_video else "image", path, "user", f"user_{i}",
                              duration=float(item.get("duration") or 0)))
    return out
