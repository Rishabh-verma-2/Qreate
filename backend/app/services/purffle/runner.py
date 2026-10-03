"""Subprocess runner for invoking PurffleShorts CLI safely."""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Default verified Purffle environment path
DEFAULT_PURFFLE_PYTHON = r"C:\Users\NISHANT\.gemini\antigravity-ide\brain\ea9bd040-c11f-49f5-b1c5-cc4541a8e963\scratch\purffle-shorts\venv\Scripts\python.exe"
DEFAULT_PURFFLE_CWD = r"C:\Users\NISHANT\.gemini\antigravity-ide\brain\ea9bd040-c11f-49f5-b1c5-cc4541a8e963\scratch\purffle-shorts"


@dataclass
class PurffleRenderResult:
    ok: bool
    mp4_path: Optional[str] = None
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    render_time_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None


def get_purffle_python_exe() -> str:
    """Resolve the Python executable to run PurffleShorts."""
    custom_path = os.environ.get("PURFFLE_PYTHON_EXE")
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    if os.path.isfile(DEFAULT_PURFFLE_PYTHON):
        return DEFAULT_PURFFLE_PYTHON
    return sys.executable


def get_purffle_cwd() -> str:
    """Resolve the working directory for Purffle execution."""
    custom_cwd = os.environ.get("PURFFLE_CWD")
    if custom_cwd and os.path.isdir(custom_cwd):
        return custom_cwd
    if os.path.isdir(DEFAULT_PURFFLE_CWD):
        return DEFAULT_PURFFLE_CWD
    return os.getcwd()


def run_purffle_render(
    purffle_script_data: Dict[str, Any],
    aspect_ratio: str = "9:16",
    timeout_seconds: int = 360,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    media_dir: Optional[str] = None,
) -> PurffleRenderResult:
    """Execute Purffle video rendering using the CLI in an isolated subprocess.

    Args:
        purffle_script_data: Purffle-compatible script dictionary.
        aspect_ratio: Output aspect ratio ("9:16", "16:9", "1:1", "4:5").
        timeout_seconds: Subprocess timeout in seconds.
        progress_callback: Optional callback for progress percentages.
        media_dir: Optional directory containing pre-sourced scene visual assets.

    Returns:
        PurffleRenderResult with status and MP4 details.
    """
    python_exe = get_purffle_python_exe()
    cwd = get_purffle_cwd()
    
    t0 = time.time()
    logger.info(f"Starting Purffle render with {python_exe} in {cwd}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        script_file = os.path.join(tmp_dir, "purffle_input_script.json")
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(purffle_script_data, f, ensure_ascii=False, indent=2)

        cmd = [
            python_exe,
            "-m",
            "purffle_shorts",
            "make",
            "--script",
            script_file,
            "--no-upload",
            "--aspect",
            aspect_ratio,
            "--resolution",
            "1080x1920",
            "--grade",
            "cinematic",
            "--caption-style",
            "bold",
            "--caption-position",
            "center",
            "--transition",
            "random",
        ]

        env = os.environ.copy()
        env["CAPTION_STYLE"] = "bold"
        env["CAPTION_POSITION"] = "center"
        env["COLOR_GRADE"] = "cinematic"
        env["KEN_BURNS"] = "true"
        env["CAPTION_MAX_WORDS"] = "3"
        env["CAPTION_UPPERCASE"] = "true"

        if media_dir and os.path.isdir(media_dir):
            cmd += ["--visuals", "local"]
            env["MEDIA_DIR"] = str(Path(media_dir).resolve())
            env["VISUAL_SOURCES"] = "local"

        if progress_callback:
            progress_callback(10, "Initializing PurffleShorts rendering pipeline...")

        try:
            process = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"Purffle render timed out after {timeout_seconds}s")
            return PurffleRenderResult(
                ok=False,
                error_message=f"Purffle rendering process timed out after {timeout_seconds} seconds",
                stdout=e.stdout or "",
                stderr=e.stderr or "",
            )
        except Exception as e:
            logger.exception("Failed to execute Purffle process")
            return PurffleRenderResult(
                ok=False,
                error_message=f"Process execution error: {str(e)}",
            )

        render_time = time.time() - t0
        stdout = process.stdout or ""
        stderr = process.stderr or ""

        if process.returncode != 0:
            logger.error(f"Purffle returned non-zero exit code {process.returncode}:\n{stderr or stdout}")
            return PurffleRenderResult(
                ok=False,
                render_time_seconds=render_time,
                stdout=stdout,
                stderr=stderr,
                error_message=f"Purffle render failed (exit code {process.returncode}): {stderr[-300:] or stdout[-300:]}",
            )

        # Parse output MP4 path from stdout
        # e.g.: "Rendered Title #shorts (26.0s video) in 15s -> C:\path\short.mp4"
        mp4_path = None
        match = re.search(r"->\s*([^\r\n]+\.mp4)", stdout)
        if match:
            candidate = match.group(1).strip()
            if os.path.isfile(candidate):
                mp4_path = candidate

        # Fallback: Check the most recently modified mp4 in cwd/output_videos
        if not mp4_path:
            output_dir = Path(cwd) / "output_videos"
            if output_dir.is_dir():
                mp4_files = sorted(output_dir.glob("*/*.mp4"), key=os.path.getmtime, reverse=True)
                if mp4_files and mp4_files[0].is_file():
                    mp4_path = str(mp4_files[0])

        if not mp4_path or not os.path.isfile(mp4_path):
            return PurffleRenderResult(
                ok=False,
                render_time_seconds=render_time,
                stdout=stdout,
                stderr=stderr,
                error_message="Purffle completed with exit code 0 but generated MP4 could not be located",
            )

        # Verify MP4 size and duration
        file_size = os.path.getsize(mp4_path)
        duration_seconds = 0.0
        dur_match = re.search(r"\((\d+(?:\.\d+)?)s\s+video\)", stdout)
        if dur_match:
            duration_seconds = float(dur_match.group(1))

        if progress_callback:
            progress_callback(100, "Purffle video rendering completed successfully.")

        logger.info(f"Purffle render succeeded: {mp4_path} ({file_size / (1024*1024):.2f} MB, {duration_seconds}s)")
        return PurffleRenderResult(
            ok=True,
            mp4_path=mp4_path,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size,
            render_time_seconds=render_time,
            stdout=stdout,
            stderr=stderr,
        )
