"""Unit tests for WanVideoEngine and resolution helpers."""

import pytest
from app.services.video.wan_engine import _resolution_for_size, WanVideoEngine
from tests.mocks.mock_wan import MockWanEngine


def test_resolution_for_size():
    """Verify aspect ratio calculations for various model sizes."""
    assert _resolution_for_size("480p", "16:9") == (832, 480)
    assert _resolution_for_size("480p", "9:16") == (480, 832)
    assert _resolution_for_size("720p", "16:9") == (1280, 720)
    assert _resolution_for_size("720p", "9:16") == (720, 1280)
    assert _resolution_for_size("1.3b", "1:1") == (640, 640)


def test_wan_engine_initialization():
    """Verify WanVideoEngine initializes without error."""
    engine = WanVideoEngine()
    assert isinstance(engine, WanVideoEngine)


@pytest.mark.asyncio
async def test_mock_wan_engine():
    """Verify MockWanEngine generates scene clip files as expected."""
    mock_engine = MockWanEngine()
    assert mock_engine.is_available() is True

    path = await mock_engine.generate_scene(
        prompt="A glowing starfield",
        duration=4,
    )
    assert path.endswith(".mp4")
    assert len(mock_engine.generated_scenes) == 1
    assert mock_engine.generated_scenes[0]["duration"] == 4
