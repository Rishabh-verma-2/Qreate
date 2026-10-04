"""Background music from Openverse (CC0 loops, mostly Freesound) matched to the script mood."""

import asyncio
import logging
import random
from typing import List, Optional

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


async def fetch_music(mood: str, dest: str, timeout_seconds: float = 5.0) -> Optional[str]:
    """Download a CC0 track for `mood` to `dest`. Returns path or None (music is optional)."""
    try:
        return await asyncio.wait_for(_fetch_music_inner(mood, dest), timeout=timeout_seconds)
    except (asyncio.TimeoutError, Exception) as e:
        logger.info(f"Music fetch timed out or skipped ({e}); continuing voice-only")
        return None


async def _fetch_music_inner(mood: str, dest: str) -> Optional[str]:
    queries = list(MOOD_QUERIES.get(mood, MOOD_QUERIES["cinematic"]))
    random.shuffle(queries)
    for q in queries[:2]:
        results = _cache.get(q)
        if results is None:
            data = await get_json(
                "https://api.openverse.org/v1/audio/",
                params={"q": q, "license": "cc0", "page_size": 15, "mature": "false"},
            ) or {}
            results = [
                r for r in data.get("results", [])
                if 15_000 <= (r.get("duration") or 0) <= 120_000
                and (r.get("filesize") or 0) <= 3_500_000
                and r.get("url")
                and (r.get("filetype") or "").startswith("mp3")
                and not any(w in (r.get("title") or "").lower() for w in ("voice", "speech", "vocal", "sfx", "effect"))
            ]
            # Prioritize smaller files to ensure fast download under 2-3s
            results.sort(key=lambda r: r.get("filesize") or 9_999_999)
            _cache.set(q, results)
        for r in results[:2]:
            if await download(r["url"], dest, min_bytes=40_000, timeout_seconds=4.0):
                logger.info(f"Music: '{r.get('title')}' ({r.get('license')}) for mood={mood}")
                return dest
    logger.info(f"No fast music found for mood={mood}; continuing voice-only")
    return None


async def detect_beats(path: str, max_seconds: float = 35.0) -> List[float]:
    """Onset times (seconds) of the music, for cutting on the beat. [] on failure.

    Spectral-flux onset detection on a 11 kHz mono decode — light enough for CPU.
    """
    from app.services.media.ffmpeg import ffmpeg_bin

    proc = await asyncio.create_subprocess_exec(
        ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-t", str(max_seconds), "-i", path,
        "-ac", "1", "-ar", "11025", "-f", "f32le", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    raw, _ = await proc.communicate()
    if not raw:
        return []
    return await asyncio.to_thread(_onsets, raw)


def _onsets(raw: bytes) -> List[float]:
    import numpy as np

    sr, hop, win = 11025, 256, 1024
    x = np.frombuffer(raw, dtype=np.float32)
    if x.size < win * 4:
        return []
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.maximum(np.diff(np.log1p(mag), axis=0), 0).sum(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    # Peaks above an adaptive threshold, at least ~0.25 s apart
    min_gap = int(0.25 * sr / hop)
    local = np.convolve(flux, np.ones(16) / 16, mode="same")
    peaks, last = [], -min_gap
    for i in range(1, len(flux) - 1):
        if flux[i] > local[i] + 0.8 and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and i - last >= min_gap:
            peaks.append((i + 1) * hop / sr)
            last = i
    return peaks
