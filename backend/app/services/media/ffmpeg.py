"""Async FFmpeg helpers. Subprocesses never block the event loop, so the API stays
responsive while videos render."""

import asyncio
import logging
import re
import shutil
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    pass


@lru_cache()
def ffmpeg_bin() -> str:
    """System FFmpeg (Docker image) if present, otherwise the imageio-ffmpeg bundle."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


async def run_ffmpeg(args: List[str], timeout: float = 600) -> str:
    """Run ffmpeg with `args`; return stderr. Raises FFmpegError on failure."""
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise FFmpegError(f"ffmpeg timed out after {timeout:.0f}s")
    err = stderr.decode(errors="replace")
    if proc.returncode != 0:
        raise FFmpegError(err.strip()[-800:] or f"ffmpeg exited {proc.returncode}")
    return err


async def probe_duration(path: str) -> float:
    """Media duration in seconds (0.0 if unknown)."""
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_bin(), "-hide_banner", "-i", path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr.decode(errors="replace"))
    if not m:
        return 0.0
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)
