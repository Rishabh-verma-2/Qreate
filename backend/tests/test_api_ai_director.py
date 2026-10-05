"""Integration tests for AI Director API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from tests.mocks.mock_llm import SAMPLE_VIDEO_PLAN_DICT, MockQwenClient


@pytest.mark.asyncio
async def test_api_diagnostics_endpoint():
    """Verify /api/videos/diagnostics returns 200 and expected diagnostic keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/videos/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert "gpu" in data
        assert "qwen" in data
        assert "comfyui" in data
        assert "wan" in data


@pytest.mark.asyncio
async def test_api_plan_endpoint(monkeypatch):
    """Verify /api/videos/plan creates and returns a valid VideoPlan."""
    mock_client = MockQwenClient()
    monkeypatch.setattr("app.services.llm.video_director.get_qwen_client", lambda: mock_client)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "prompt": "Create a 15-second cinematic space journey",
            "style": "cinematic 3D animation",
            "duration": 15,
            "aspect_ratio": "16:9",
        }
        resp = await client.post("/api/videos/plan", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert data["status"] == "completed"
        assert data["plan"]["title"] == "Cosmic Voyage: Into the Black Hole"
