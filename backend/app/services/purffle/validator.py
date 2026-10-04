"""Output validation for PurffleShorts rendered MP4s."""

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional
import imageio_ffmpeg

logger = logging.getLogger(__name__)


@dataclass
class VideoValidationResult:
    is_valid: bool
    mp4_path: str
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: str = ""
    has_audio: bool = False
    error: Optional[str] = None


def validate_purffle_mp4(mp4_path: str, expected_aspect: str = "9:16") -> VideoValidationResult:
    """Validate that the generated Purffle MP4 exists, is non-empty, has a valid container,
    expected resolution / portrait orientation, and an audio stream."""
    if not mp4_path or not os.path.isfile(mp4_path):
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path or "",
            error=f"MP4 file does not exist at path: {mp4_path}",
        )

    file_size = os.path.getsize(mp4_path)
    if file_size <= 0:
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path,
            error=f"MP4 file is empty (0 bytes): {mp4_path}",
        )

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        proc = subprocess.run(
            [ffmpeg_exe, "-i", mp4_path],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        stderr = proc.stderr
    except Exception as e:
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path,
            file_size_bytes=file_size,
            error=f"Failed to inspect MP4 with ffmpeg: {e}",
        )

    # 1. Parse Duration
    duration = 0.0
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if dur_match:
        h, m, s = dur_match.groups()
        duration = int(h) * 3600 + int(m) * 60 + float(s)

    # 2. Check Video Stream & Resolution
    # e.g.: Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1080x1920 [SAR 1:1 DAR 9:16]
    video_match = re.search(r"Stream\s+#\d+:\d+.*?: Video:\s*([^,\n]+).*?,\s*(\d{2,5})x(\d{2,5})", stderr)
    if not video_match:
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path,
            file_size_bytes=file_size,
            error="No valid video stream found in container",
        )

    video_codec = video_match.group(1).strip()
    width = int(video_match.group(2))
    height = int(video_match.group(3))

    # Check expected portrait aspect (9:16)
    if expected_aspect == "9:16" and height <= width:
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path,
            file_size_bytes=file_size,
            duration_seconds=duration,
            width=width,
            height=height,
            video_codec=video_codec,
            error=f"Expected portrait video for 9:16, but got resolution {width}x{height} (height <= width)",
        )

    # 3. Check Audio Stream
    # e.g.: Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D)
    audio_match = re.search(r"Stream\s+#\d+:\d+.*?: Audio:\s*([^,\n]+)", stderr)
    if not audio_match:
        return VideoValidationResult(
            is_valid=False,
            mp4_path=mp4_path,
            file_size_bytes=file_size,
            duration_seconds=duration,
            width=width,
            height=height,
            video_codec=video_codec,
            error="No valid audio stream found in container",
        )

    audio_codec = audio_match.group(1).strip()

    logger.info(
        f"MP4 validation PASSED for {mp4_path}: {width}x{height}, {duration:.2f}s, "
        f"video={video_codec}, audio={audio_codec}, size={file_size} bytes"
    )

    return VideoValidationResult(
        is_valid=True,
        mp4_path=mp4_path,
        file_size_bytes=file_size,
        duration_seconds=duration,
        width=width,
        height=height,
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=True,
    )
