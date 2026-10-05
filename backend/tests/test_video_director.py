"""Tests for AI Video Director and VideoPlan schema validation."""

import pytest
from app.services.llm.schemas import VideoPlan, Scene, validate_video_plan
from app.services.llm.video_director import QwenVideoDirector
from tests.mocks.mock_llm import SAMPLE_VIDEO_PLAN_DICT, MockQwenClient


def test_validate_video_plan_success():
    """Verify that a well-formed JSON dictionary validates into a VideoPlan model."""
    plan = validate_video_plan(SAMPLE_VIDEO_PLAN_DICT)
    assert isinstance(plan, VideoPlan)
    assert plan.title == "Cosmic Voyage: Into the Black Hole"
    assert len(plan.scenes) == 3
    assert plan.characters[0].name == "Captain Vance"
    assert plan.scenes[0].camera.movement == "dolly-in"


def test_validate_video_plan_invalid():
    """Verify that invalid plan data raises a ValueError."""
    invalid_dict = {"title": "Incomplete"}
    with pytest.raises(Exception):
        validate_video_plan(invalid_dict)


@pytest.mark.asyncio
async def test_qwen_video_director_plan(monkeypatch):
    """Test QwenVideoDirector using MockQwenClient."""
    mock_client = MockQwenClient()
    monkeypatch.setattr("app.services.llm.video_director.get_qwen_client", lambda: mock_client)

    director = QwenVideoDirector()
    plan = await director.plan(
        prompt="A 15 second journey into a black hole",
        style="cinematic 3D animation",
        duration=15,
        aspect_ratio="16:9",
    )

    assert isinstance(plan, VideoPlan)
    assert plan.total_duration == 15
    assert len(plan.scenes) == 3
    assert mock_client.call_count == 1


@pytest.mark.asyncio
async def test_qwen_video_director_retry_on_invalid_json(monkeypatch):
    """Test that QwenVideoDirector retries once if first attempt returns invalid JSON."""
    mock_client = MockQwenClient(fail_first=True)
    monkeypatch.setattr("app.services.llm.video_director.get_qwen_client", lambda: mock_client)

    director = QwenVideoDirector()
    plan = await director.plan(
        prompt="Black hole travel",
        duration=15,
    )

    assert isinstance(plan, VideoPlan)
    assert mock_client.call_count == 2
