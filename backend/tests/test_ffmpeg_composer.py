"""Tests for wan_pipeline ffmpeg_composer."""

import pytest
from app.services.wan_pipeline.ffmpeg_composer import wan_compose


@pytest.mark.asyncio
async def test_wan_compose_empty_clips():
    """Verify wan_compose raises ValueError when no scene clips provided."""
    with pytest.raises(ValueError, match="No scene clips to compose"):
        await wan_compose(
            scene_clips=[],
            scene_audio=[],
            scene_durations=[],
            output_path="output.mp4",
        )
