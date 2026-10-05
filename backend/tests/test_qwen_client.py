"""Tests for the QwenClient."""

import pytest
import httpx
from app.services.llm.qwen_client import QwenClient, _strip_thinking
from app.core.errors import QwenUnavailableError, QwenError


def test_strip_thinking():
    raw = "<think>Let me plan this video...</think>{\"title\": \"Test\"}"
    cleaned = _strip_thinking(raw)
    assert cleaned == "{\"title\": \"Test\"}"

    raw_no_think = "{\"title\": \"No Think\"}"
    assert _strip_thinking(raw_no_think) == raw_no_think


@pytest.mark.asyncio
async def test_qwen_client_ping_failure(monkeypatch):
    """Test that ping returns False when server is unreachable."""
    client = QwenClient()

    async def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    assert await client.ping() is False


@pytest.mark.asyncio
async def test_qwen_client_chat_success(monkeypatch):
    """Test chat method returns assistant content."""
    client = QwenClient()

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "choices": [
                    {"message": {"content": "<think>Thinking</think>Hello from Qwen!"}}
                ]
            }

    async def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    res = await client.chat([{"role": "user", "content": "Hi"}])
    assert res == "Hello from Qwen!"
