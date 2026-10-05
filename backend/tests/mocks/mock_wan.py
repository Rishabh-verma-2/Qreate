"""Mock Wan2.1 Video Engine for testing."""

import os
import tempfile
from typing import Optional
from app.services.video.base import VideoEngine


class MockWanEngine(VideoEngine):
    """Mock video engine that simulates fast generation of scene video files."""

    def __init__(self, available: bool = True):
        self._available = available
        self.generated_scenes = []

    def is_available(self) -> bool:
        return self._available

    async def generate_scene(
        self,
        prompt: str,
        image: Optional[str] = None,
        duration: int = 5,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        output_path: str = "",
    ) -> str:
        self.generated_scenes.append({
            "prompt": prompt,
            "image": image,
            "duration": duration,
        })
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

        # Write dummy binary content representing an MP4 container header
        with open(output_path, "wb") as f:
            f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free")

        return output_path
