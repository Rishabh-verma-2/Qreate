"""Background music from Openverse (CC0 loops, mostly Freesound) matched to the script mood."""

import logging
import random
from typing import Optional

from app.services.media.http import TTLCache, download, get_json

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=64)

MOOD_QUERIES = {
    "upbeat": ["upbeat loop", "funky upbeat loop", "happy pop loop"],
    "chill": ["chill loop", "chill lofi loop", "ambient chill"],
    "lofi": ["lofi loop", "lofi hip hop loop", "chill lofi melody loop"],
    "cinematic": ["cinematic ambient", "cinematic loop", "epic ambient"],
    "inspiring": ["inspiring piano loop", "uplifting loop", "motivational loop"],
    "dramatic": ["dramatic cinematic", "tension ambient", "dark cinematic loop"],
    "emotional": ["emotional piano", "sad piano loop", "romantic piano"],
    "corporate": ["corporate loop", "technology upbeat loop", "positive corporate"],
}


async def fetch_music(mood: str, dest: str) -> Optional[str]:
    """Download a CC0 track for `mood` to `dest`. Returns path or None (music is optional)."""
    queries = list(MOOD_QUERIES.get(mood, MOOD_QUERIES["cinematic"]))
    random.shuffle(queries)
    for q in queries:
        results = _cache.get(q)
        if results is None:
            data = await get_json(
                "https://api.openverse.org/v1/audio/",
                params={"q": q, "license": "cc0", "page_size": 20, "mature": "false"},
            ) or {}
            results = [
                r for r in data.get("results", [])
                if (r.get("duration") or 0) >= 15_000 and r.get("url")
                and (r.get("filetype") or "").startswith("mp3")
                and not any(w in (r.get("title") or "").lower() for w in ("voice", "speech", "vocal", "sfx", "effect"))
            ]
            _cache.set(q, results)
        random.shuffle(results)
        for r in results[:4]:
            if await download(r["url"], dest, min_bytes=40_000):
                logger.info(f"Music: '{r.get('title')}' ({r.get('license')}) for mood={mood}")
                return dest
    logger.info(f"No music found for mood={mood}; continuing voice-only")
    return None
