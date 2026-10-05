"""Wan2.1 Video Engine — generates scene clips via ComfyUI or direct CLI.

Generation priority:
  1. ComfyUI (preferred) — managed via comfyui_client.py
  2. Direct Wan CLI      — subprocess call when ComfyUI is unavailable

Supports both:
  - Text-to-Video (T2V): WAN_MODE=t2v or no reference image
  - Image-to-Video (I2V): WAN_MODE=i2v with a character reference image

Configuration (all via environment variables):
  VIDEO_ENGINE=wan
  WAN_MODE=t2v|i2v
  WAN_MODEL_PATH=/path/to/wan/model
  WAN_MODEL_SIZE=480P|720P|1.3B
  COMFYUI_BASE_URL=http://localhost:8188
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from app.core.config import get_settings
from app.core.errors import WanError
from app.services.video.base import VideoEngine
from app.services.video.comfyui_client import get_comfyui_client

logger = logging.getLogger(__name__)

# Default negative prompt for Wan2.1 to avoid common artifacts
DEFAULT_NEGATIVE = (
    "blurry, low quality, watermark, text, logo, subtitle, bad anatomy, "
    "distorted face, ugly, artifact, noise, overexposed"
)


def _resolution_for_size(size: str, aspect_ratio: str = "16:9") -> tuple[int, int]:
    """Return (width, height) for a given WAN_MODEL_SIZE and aspect ratio."""
    # Base resolutions per model size
    size_map = {
        "1.3b": {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)},
        "480p": {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)},
        "720p": {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (960, 960)},
    }
    key = size.lower().replace("-", "")
    ar = aspect_ratio.lower()
    return size_map.get(key, size_map["480p"]).get(ar, (832, 480))


class WanVideoEngine(VideoEngine):
    """Wan2.1 video generation engine.

    Tries ComfyUI first (if available), then falls back to direct CLI.
    """

    def __init__(self):
        self._s = get_settings()
        self._comfyui = get_comfyui_client()
        self._comfyui_available: Optional[bool] = None  # cached after first check

    def is_available(self) -> bool:
        """Return True if at least one Wan backend is configured."""
        return bool(self._s.WAN_MODEL_PATH or self._s.COMFYUI_BASE_URL)

    async def _comfyui_ready(self) -> bool:
        """Check ComfyUI availability (cached for the process lifetime)."""
        if self._comfyui_available is None:
            self._comfyui_available = await self._comfyui.is_available()
            if self._comfyui_available:
                logger.info("WanVideoEngine: using ComfyUI backend")
            else:
                logger.info("WanVideoEngine: ComfyUI not available, using direct CLI fallback")
        return self._comfyui_available

    async def generate_scene(
        self,
        prompt: str,
        image: Optional[str] = None,
        duration: int = 5,
        width: int = 832,
        height: int = 480,
        fps: int = 24,
        output_path: str = "",
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
    ) -> str:
        """Generate a single scene MP4.

        Args:
            prompt: Visual description prompt for Wan2.1.
            image: Path to a reference image (triggers I2V mode if set).
            duration: Clip duration in seconds.
            width: Output width (auto-selected from WAN_MODEL_SIZE if not specified).
            height: Output height.
            fps: Frames per second.
            output_path: Desired output path. A temp file is used if not specified.
            negative_prompt: What to exclude from generation.
            aspect_ratio: "16:9" | "9:16" | "1:1"

        Returns:
            Absolute path to the generated MP4.
        """
        # Determine resolution from config if defaults are passed
        if width == 832 and height == 480:
            width, height = _resolution_for_size(self._s.WAN_MODEL_SIZE, aspect_ratio)

        neg = negative_prompt or DEFAULT_NEGATIVE
        use_i2v = (image is not None) and (self._s.WAN_MODE == "i2v")

        # Set up output path
        if not output_path:
            tmp_dir = tempfile.mkdtemp(prefix="wan_scene_")
            output_path = os.path.join(tmp_dir, "scene.mp4")

        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        logger.info(
            f"WanVideoEngine: {'I2V' if use_i2v else 'T2V'} — "
            f"{width}x{height}@{fps}fps, {duration}s, prompt={prompt[:60]}..."
        )

        # ── Attempt 1: ComfyUI ────────────────────────────────────────────────
        if await self._comfyui_ready():
            try:
                if use_i2v and image:
                    result = await self._comfyui.generate_i2v(
                        prompt=prompt,
                        negative_prompt=neg,
                        image_path=image,
                        duration=duration,
                        width=width,
                        height=height,
                        fps=fps,
                        output_dir=output_dir,
                    )
                else:
                    result = await self._comfyui.generate_t2v(
                        prompt=prompt,
                        negative_prompt=neg,
                        duration=duration,
                        width=width,
                        height=height,
                        fps=fps,
                        output_dir=output_dir,
                    )
                # ComfyUI may save with a different name — copy to output_path
                if result != output_path and os.path.exists(result):
                    shutil.copy2(result, output_path)
                    return output_path
                return result
            except Exception as e:
                logger.warning(f"ComfyUI generation failed: {e}. Trying direct CLI.")
                self._comfyui_available = False  # don't retry ComfyUI this session

        # ── Attempt 2: Direct Wan CLI ─────────────────────────────────────────
        if self._s.WAN_MODEL_PATH:
            return await self._generate_via_cli(
                prompt=prompt,
                negative_prompt=neg,
                image=image if use_i2v else None,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                output_path=output_path,
            )

        raise WanError(
            "Wan2.1 is not available: ComfyUI is not running and WAN_MODEL_PATH is not set. "
            "See docs/LOCAL_AI_SETUP.md for setup instructions."
        )

    async def _generate_via_cli(
        self,
        prompt: str,
        negative_prompt: str,
        image: Optional[str],
        duration: int,
        width: int,
        height: int,
        fps: int,
        output_path: str,
    ) -> str:
        """Run Wan2.1 via the official Python CLI (generate.py).

        This is the fallback when ComfyUI is unavailable.
        Wan2.1's generate.py is the entry point in the official repo.
        """
        model_path = self._s.WAN_MODEL_PATH
        num_frames = duration * fps

        cmd = [
            "python", os.path.join(model_path, "generate.py"),
            "--task", "i2v-14B" if image else "t2v-14B",
            "--size", f"{width}*{height}",
            "--ckpt_dir", model_path,
            "--prompt", prompt,
            "--save_file", output_path,
            "--sample_steps", "20",
            "--frame_num", str(num_frames),
        ]
        if image:
            cmd += ["--image", image]
        if negative_prompt:
            cmd += ["--sample_neg_prompt", negative_prompt]

        logger.info(f"WanVideoEngine CLI: {' '.join(cmd[:6])}...")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self._s.WAN_SCENE_TIMEOUT_SECONDS,
                cwd=model_path,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout)[-500:]
                # GPU OOM detection
                if "out of memory" in err.lower() or "cuda out of memory" in err.lower():
                    raise WanError(
                        "GPU out of memory during Wan2.1 generation. "
                        "Reduce resolution or use a smaller model (WAN_MODEL_SIZE=1.3B)."
                    )
                raise WanError(f"Wan2.1 CLI exited with code {result.returncode}: {err}")
        except subprocess.TimeoutExpired:
            raise WanError(
                f"Wan2.1 CLI timed out after {self._s.WAN_SCENE_TIMEOUT_SECONDS}s. "
                "Try shorter duration or fewer frames."
            )
        except WanError:
            raise
        except Exception as e:
            raise WanError(f"Wan2.1 CLI failed: {e}")

        if not os.path.exists(output_path):
            raise WanError(
                f"Wan2.1 CLI ran but output file not found at {output_path}. "
                "Check Wan2.1 logs for errors."
            )

        logger.info(f"WanVideoEngine: scene generated at {output_path}")
        return output_path
