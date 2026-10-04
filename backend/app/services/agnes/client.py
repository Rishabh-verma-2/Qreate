"""Agnes AI API client — video generation and chat completion."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.errors import AgnesAPIError, AgnesQueueFullError

logger = logging.getLogger(__name__)

_QUEUE_FULL_CODES = {"video_queue_full", "fail_to_fetch_task"}


class AgnesClient:
    """Async HTTP client for the Agnes AI API.

    Covers:
      - Chat completions (script generation)
      - Video task creation
      - Video task status polling
    """

    def __init__(self):
        self._settings = get_settings()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.AGNES_API_KEY}",
            "Content-Type": "application/json",
        }

    def _video_url(self, path: str = "") -> str:
        base = self._settings.AGNES_BASE_URL.rstrip("/")
        return f"{base}{path}"

    # ── Chat / Script Generation ─────────────────────────────────────────────

    async def chat_completion(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> str:
        """Call Agnes chat completions API and return the assistant's content."""
        settings = self._settings
        if not settings.AGNES_API_KEY:
            raise AgnesAPIError("AGNES_API_KEY is not configured", status_code=503)

        model = model or settings.AGNES_CHAT_MODEL
        url = self._video_url("/v1/chat/completions")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=self._headers())
            except httpx.TimeoutException:
                raise AgnesAPIError("Script generation timed out. Please try again.", status_code=504)
            except httpx.RequestError as e:
                raise AgnesAPIError(f"Network error during script generation: {e}", status_code=502)

        if resp.status_code != 200:
            err = self._extract_error(resp)
            raise AgnesAPIError(
                f"Agnes chat API error: {err['message'] or resp.text[:200]}",
                status_code=resp.status_code,
                detail=err,
            )

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise AgnesAPIError(f"Unexpected Agnes chat response format: {e}", status_code=502)

    # ── Video Generation ─────────────────────────────────────────────────────

    async def create_video_task(
        self,
        prompt: str,
        mode: str = "text",
        seconds: str = "5",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Submit a video generation task and return raw Agnes response.

        Returns dict with keys: id, video_id, task_id, model, status, etc.
        IMPORTANT: Use video_id for polling, not id.
        """
        settings = self._settings
        if not settings.AGNES_API_KEY:
            raise AgnesAPIError("AGNES_API_KEY is not configured", status_code=503)

        url = self._video_url("/v1/videos")
        payload: Dict[str, Any] = {
            "model": settings.AGNES_VIDEO_MODEL,
            "prompt": prompt,
            "mode": mode,
            "seconds": str(seconds),
            "size": settings.AGNES_VIDEO_SIZE,
            "aspect_ratio": aspect_ratio,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        logger.info(f"Submitting Agnes video task: model={settings.AGNES_VIDEO_MODEL} mode={mode} duration={seconds}s")

        # Retry loop for queue full (503)
        started_at = time.monotonic()
        max_queue_wait = settings.VIDEO_QUEUE_RETRY_MAX_SECONDS
        retry_delay = 30.0

        while True:
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    resp = await client.post(url, json=payload, headers=self._headers())
                except httpx.TimeoutException:
                    raise AgnesAPIError("Video task submission timed out", status_code=504)
                except httpx.RequestError as e:
                    raise AgnesAPIError(f"Network error: {e}", status_code=502)

            if resp.status_code == 200:
                data = resp.json()
                # Extract the correct video_id for polling (must use video_id, not id)
                video_id = data.get("video_id") or data.get("task_id") or data.get("id")
                data["_polling_video_id"] = video_id
                logger.info(f"Agnes video task created: video_id={video_id}")
                return data

            # Check for queue-full 503
            if resp.status_code == 503:
                err = self._extract_error(resp)
                code = err.get("code", "")
                if code in _QUEUE_FULL_CODES:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= max_queue_wait:
                        raise AgnesQueueFullError(waited_seconds=int(elapsed))
                    wait = min(retry_delay, max_queue_wait - elapsed)
                    logger.warning(f"Agnes queue full ({code}), retrying in {wait:.0f}s (elapsed {elapsed:.0f}s)")
                    await asyncio.sleep(wait)
                    continue

            # Other errors
            err = self._extract_error(resp)
            raise AgnesAPIError(
                f"Agnes video API error ({resp.status_code}): {err.get('message', resp.text[:200])}",
                status_code=resp.status_code,
                detail=err,
            )

    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Poll Agnes for video task status.

        NOTE: Always returns HTTP 200 even for failed tasks.
        Check body 'status' field, not HTTP code.

        Returns dict with: status, url (nullable), progress, error (nullable object), etc.
        """
        settings = self._settings
        url = (
            f"{settings.AGNES_BASE_URL}/agnesapi"
            f"?video_id={video_id}&model_name={settings.AGNES_VIDEO_MODEL}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, headers=self._headers())
            except httpx.TimeoutException:
                raise AgnesAPIError("Polling timed out", status_code=504)
            except httpx.RequestError as e:
                raise AgnesAPIError(f"Network error polling status: {e}", status_code=502)

        if resp.status_code != 200:
            err = self._extract_error(resp)
            raise AgnesAPIError(
                f"Agnes status API error ({resp.status_code}): {err.get('message', '')}",
                status_code=resp.status_code,
            )

        data = resp.json()
        # Normalize error field — Agnes returns error as object {code, message}, not string
        if isinstance(data.get("error"), dict):
            err_obj = data["error"]
            data["error_code"] = str(err_obj.get("code", ""))
            data["error_message"] = str(err_obj.get("message", ""))
        elif data.get("error") is None:
            data["error_code"] = ""
            data["error_message"] = ""
        return data

    async def get_available_models(self) -> Dict[str, Any]:
        """Fetch available Agnes models."""
        url = self._video_url("/v1/models")
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"Failed to fetch Agnes models: {e}")
        return {"data": []}

    @staticmethod
    def _extract_error(resp: httpx.Response) -> Dict[str, str]:
        """Extract code/message from error response body."""
        try:
            data = resp.json()
            if isinstance(data, dict):
                code = str(data.get("code") or "")
                message = str(data.get("message") or data.get("detail") or "")
                err = data.get("error")
                if isinstance(err, dict):
                    code = code or str(err.get("code") or "")
                    message = message or str(err.get("message") or "")
                return {"code": code, "message": message}
        except Exception:
            pass
        return {"code": "", "message": resp.text[:300] if resp.text else ""}


def get_agnes_client() -> AgnesClient:
    return AgnesClient()
