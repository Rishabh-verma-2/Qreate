"""Video engine factory.

Usage::

    from app.services.video import get_video_engine

    engine = get_video_engine()
    clip_path = await engine.generate_scene(
        prompt="A glowing black hole in deep space",
        duration=5,
    )
"""

from app.core.config import get_settings
from app.services.video.base import VideoEngine


def get_video_engine() -> VideoEngine:
    """Return the configured VideoEngine implementation.

    ENGINE selection (VIDEO_ENGINE env var):
      - "wan"    → WanVideoEngine (Wan2.1 via ComfyUI or CLI, requires GPU)
      - "native" → NativeVideoEngine (existing animated motion graphics, no GPU)
    """
    s = get_settings()
    engine_name = s.VIDEO_ENGINE.lower()

    if engine_name == "wan":
        from app.services.video.wan_engine import WanVideoEngine
        return WanVideoEngine()

    # Default: native animated motion graphics (no GPU required)
    from app.services.video.native_engine import NativeVideoEngine
    return NativeVideoEngine()


__all__ = ["VideoEngine", "get_video_engine"]
