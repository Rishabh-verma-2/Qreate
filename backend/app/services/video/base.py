"""Abstract base class for video generation engines.

Concrete implementations:
- NativeVideoEngine  — wraps the existing animated motion graphics engine
- WanVideoEngine     — Wan2.1 via ComfyUI (preferred) or direct CLI
"""

from abc import ABC, abstractmethod
from typing import Optional


class VideoEngine(ABC):
    """Common interface for all video generation backends.

    Each engine takes a text prompt (and optionally a reference image)
    and produces a silent MP4 clip for a single scene.
    """

    @abstractmethod
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
    ) -> str:
        """Generate a single scene MP4 file.

        Args:
            prompt: Text description of the scene visuals.
            image: Optional path to a reference image (enables I2V mode).
            duration: Clip duration in seconds.
            width: Output width in pixels.
            height: Output height in pixels.
            fps: Frames per second.
            output_path: Where to write the output MP4. If empty, a temp path is used.
            negative_prompt: Things to avoid in the generation.

        Returns:
            Absolute path to the generated MP4 file.

        Raises:
            WanError: If generation fails.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this engine can currently generate scenes."""
        ...

    @property
    def name(self) -> str:
        """Human-readable engine name for logging."""
        return self.__class__.__name__
