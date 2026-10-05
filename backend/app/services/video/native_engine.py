"""NativeVideoEngine — wraps the existing animated motion graphics engine.

This thin wrapper satisfies the VideoEngine interface using the existing
free_generator.py motion graphics system. It's the fallback when Wan2.1
is not configured (VIDEO_ENGINE=native, the default).

No GPU required.
"""

import logging
import os
import tempfile
from typing import Optional

from app.services.video.base import VideoEngine

logger = logging.getLogger(__name__)


class NativeVideoEngine(VideoEngine):
    """VideoEngine adapter around the existing Pillow/FFmpeg animated engine.

    This allows the AI Director pipeline to work without a GPU by generating
    motion-graphics-style clips instead of AI video.

    For production-quality AI video, use WanVideoEngine instead.
    """

    def is_available(self) -> bool:
        """Always available — uses Pillow + FFmpeg only."""
        return True

    async def generate_scene(
        self,
        prompt: str,
        image: Optional[str] = None,
        duration: int = 5,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        output_path: str = "",
        negative_prompt: str = "",
        **kwargs,
    ) -> str:
        """Generate a scene using the existing animated motion graphics system.

        This creates a Ken Burns / motion graphics clip from the prompt text,
        NOT an AI-generated video. Useful for development/testing without a GPU.

        Returns:
            Path to the generated MP4 clip.
        """
        import asyncio
        from app.services.media.ffmpeg import run_ffmpeg
        from app.services.media.composer import make_text_card, _ken_burns, _x264_args
        from app.core.config import get_settings

        s = get_settings()

        if not output_path:
            tmp = tempfile.mkdtemp(prefix="native_scene_")
            output_path = os.path.join(tmp, "scene.mp4")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate a text card image from the prompt
        card_path = output_path.replace(".mp4", "_card.jpg")
        # Use prompt as text card content (truncated to ~50 chars)
        card_text = prompt[:80].rsplit(" ", 1)[0] if len(prompt) > 80 else prompt

        try:
            make_text_card(card_text, card_path)
        except Exception as e:
            logger.warning(f"NativeVideoEngine: text card failed ({e}), using gradient")
            from app.services.media.stock import create_gradient_background
            card_path = create_gradient_background(card_path, seed=hash(prompt) % 100)

        W, H = width, height
        frames = max(int(duration * fps), 1)
        kb = _ken_burns(0, frames, W, H, fps)
        vf = f"scale={W}:{H}:force_original_aspect_ratio=fill:flags=lanczos,crop={W}:{H},{kb},setsar=1,format=yuv420p"

        args = [
            "-loop", "1", "-framerate", str(fps), "-i", card_path,
            "-vf", vf, "-frames:v", str(frames), "-an",
            *_x264_args(22), output_path,
        ]
        await run_ffmpeg(args, timeout=120)

        logger.info(
            f"NativeVideoEngine: scene generated at {output_path} "
            f"({duration}s, {W}x{H}). NOTE: Using motion graphics, not Wan AI video."
        )
        return output_path
