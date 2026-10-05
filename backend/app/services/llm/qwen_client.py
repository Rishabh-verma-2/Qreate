"""Dedicated Qwen3 / vLLM OpenAI-compatible client.

Connects to a locally running vLLM server that serves Qwen3-8B.
Start the server with:
    vllm serve Qwen/Qwen3-8B --port 8000 --api-key EMPTY

This client is separate from the multi-provider llm/client.py because:
- Qwen3 is always tried FIRST for AI Director tasks (it's the primary model)
- It may need special handling for thinking tokens (<think>...</think>)
- It needs its own timeout (120s vs the 60s cloud default)
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import QwenError, QwenUnavailableError

logger = logging.getLogger(__name__)

# Qwen3 wraps reasoning in <think>...</think> tags; strip them from final output
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_thinking(text: str) -> str:
    """Remove Qwen3 chain-of-thought tags from the response."""
    return _THINK_RE.sub("", text).strip()


class QwenClient:
    """Async client for the local vLLM Qwen3-8B server.

    Usage::

        client = QwenClient()
        if await client.ping():
            response = await client.chat([
                {"role": "system", "content": "You are a video director."},
                {"role": "user", "content": "Plan a 30s video about black holes."},
            ])
    """

    def __init__(self):
        s = get_settings()
        self.base_url = s.QWEN_BASE_URL.rstrip("/")
        self.model = s.QWEN_MODEL
        self.api_key = s.QWEN_API_KEY or "EMPTY"
        self.timeout = s.QWEN_TIMEOUT_SECONDS
        self.max_tokens = s.QWEN_MAX_TOKENS

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def ping(self) -> bool:
        """Return True if the vLLM server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._headers,
                )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"Qwen ping failed: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """Send a chat completion request to the vLLM server.

        Returns:
            The assistant's text response (thinking tokens stripped).

        Raises:
            QwenUnavailableError: if the server is not reachable.
            QwenError: on HTTP errors or unexpected response shape.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
        except httpx.ConnectError:
            raise QwenUnavailableError()
        except httpx.TimeoutException:
            raise QwenError(
                f"Request timed out after {self.timeout}s. "
                "The model may be loading or the prompt is too long.",
                status_code=504,
            )
        except httpx.HTTPError as e:
            raise QwenError(f"HTTP error communicating with vLLM: {e}", status_code=502)

        if resp.status_code != 200:
            raise QwenError(
                f"vLLM returned HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=502,
            )

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise QwenError(f"Unexpected vLLM response shape: {e}", status_code=502)

        # Strip Qwen3 chain-of-thought (<think>...</think>) before returning
        cleaned = _strip_thinking(content)
        if not cleaned and content:
            # Entire response was inside <think> — return the raw content
            cleaned = content.strip()

        logger.debug(f"Qwen3 response ({len(cleaned)} chars)")
        return cleaned

    async def chat_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_attempts: int = 3,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call chat() with exponential back-off on transient failures.

        Does NOT retry QwenUnavailableError (no point retrying if server is down).
        """
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
            except QwenUnavailableError:
                raise  # propagate immediately
            except QwenError as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"Qwen attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {wait}s.")
                await asyncio.sleep(wait)
        raise QwenError(f"All {max_attempts} attempts failed. Last error: {last_error}")

    async def get_available_models(self) -> List[str]:
        """List models served by the vLLM instance."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers)
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.debug(f"Could not list Qwen models: {e}")
            return []


# Module-level singleton (lazy, not instantiated at import time)
_client: Optional[QwenClient] = None


def get_qwen_client() -> QwenClient:
    """Return the module-level QwenClient singleton."""
    global _client
    if _client is None:
        _client = QwenClient()
    return _client
