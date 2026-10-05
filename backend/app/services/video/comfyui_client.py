"""ComfyUI REST API client for Wan2.1 workflow submission.

ComfyUI exposes:
  POST /prompt           — submit a workflow
  GET  /history/{id}    — poll for completion
  POST /upload/image     — upload a reference image
  GET  /view?filename=X  — download an output file

Workflow templates live in services/video/workflows/ and are parameterized
before submission so no business logic is hardcoded in the JSON files.
"""

import asyncio
import json
import logging
import os
import re
import tempfile
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import ComfyUIError

logger = logging.getLogger(__name__)

# Directory containing workflow template JSON files
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")


def _load_workflow(filename: str) -> dict:
    """Load a workflow template JSON from the workflows directory."""
    path = os.path.join(WORKFLOWS_DIR, filename)
    if not os.path.exists(path):
        raise ComfyUIError(f"Workflow template not found: {path}", status_code=500)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _fill_template(workflow: dict, params: Dict[str, str]) -> dict:
    """Replace {{PARAM_NAME}} placeholders in a workflow with actual values.

    Works recursively through nested dicts/lists.
    """
    raw = json.dumps(workflow)
    for key, value in params.items():
        raw = raw.replace(f"{{{{{key}}}}}", str(value))
    return json.loads(raw)


class ComfyUIClient:
    """Async client for submitting Wan2.1 workflows to a local ComfyUI server."""

    def __init__(self):
        s = get_settings()
        self.base_url = s.COMFYUI_BASE_URL.rstrip("/")
        self.timeout = s.COMFYUI_TIMEOUT_SECONDS

    @property
    def _client_kwargs(self) -> dict:
        return {"timeout": 30.0, "follow_redirects": True}

    async def is_available(self) -> bool:
        """Return True if ComfyUI is reachable."""
        try:
            async with httpx.AsyncClient(**self._client_kwargs) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
            return resp.status_code == 200
        except Exception:
            return False

    async def upload_image(self, image_path: str) -> str:
        """Upload a local image file to ComfyUI and return the server filename.

        Args:
            image_path: Local path to the image.

        Returns:
            The filename as stored on the ComfyUI server (e.g. 'ref_char.png').

        Raises:
            ComfyUIError: If upload fails.
        """
        if not os.path.exists(image_path):
            raise ComfyUIError(f"Reference image not found: {image_path}", status_code=400)

        filename = os.path.basename(image_path)
        try:
            async with httpx.AsyncClient(**self._client_kwargs) as client:
                with open(image_path, "rb") as f:
                    files = {"image": (filename, f, "image/png")}
                    resp = await client.post(f"{self.base_url}/upload/image", files=files)
            if resp.status_code != 200:
                raise ComfyUIError(
                    f"Image upload returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            server_name = data.get("name") or filename
            logger.debug(f"ComfyUI image uploaded: {image_path} → {server_name}")
            return server_name
        except ComfyUIError:
            raise
        except Exception as e:
            raise ComfyUIError(f"Image upload failed: {e}")

    async def submit_workflow(self, workflow: dict) -> str:
        """Submit a workflow to ComfyUI and return the prompt_id.

        Args:
            workflow: Fully parameterized ComfyUI workflow dict.

        Returns:
            prompt_id string used to poll for completion.

        Raises:
            ComfyUIError: If submission fails.
        """
        payload = {"prompt": workflow}
        try:
            async with httpx.AsyncClient(**self._client_kwargs) as client:
                resp = await client.post(f"{self.base_url}/prompt", json=payload)
            if resp.status_code != 200:
                body = resp.text[:500]
                raise ComfyUIError(
                    f"Workflow submission returned HTTP {resp.status_code}: {body}"
                )
            data = resp.json()
            prompt_id = data.get("prompt_id")
            if not prompt_id:
                raise ComfyUIError("ComfyUI did not return a prompt_id")
            logger.info(f"ComfyUI workflow submitted: {prompt_id}")
            return prompt_id
        except ComfyUIError:
            raise
        except Exception as e:
            raise ComfyUIError(f"Workflow submission failed: {e}")

    async def wait_for_output(
        self,
        prompt_id: str,
        output_dir: str,
        poll_interval: float = 3.0,
        timeout: Optional[int] = None,
    ) -> str:
        """Poll ComfyUI until the workflow completes and download the output MP4.

        Args:
            prompt_id: The prompt_id returned by submit_workflow().
            output_dir: Local directory to download the output video into.
            poll_interval: Seconds between status polls.
            timeout: Max seconds to wait (defaults to COMFYUI_TIMEOUT_SECONDS).

        Returns:
            Local path to the downloaded output MP4.

        Raises:
            ComfyUIError: On timeout or workflow failure.
        """
        deadline = time.monotonic() + (timeout or self.timeout)
        os.makedirs(output_dir, exist_ok=True)

        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)
            try:
                async with httpx.AsyncClient(**self._client_kwargs) as client:
                    resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if prompt_id not in data:
                    continue  # not done yet
                history = data[prompt_id]
                # Check for errors
                status = history.get("status", {})
                if status.get("status_str") == "error":
                    msgs = status.get("messages", [])
                    raise ComfyUIError(
                        f"Workflow failed: {msgs[-1] if msgs else 'unknown error'}"
                    )
                # Find output videos
                outputs = history.get("outputs", {})
                for node_id, node_out in outputs.items():
                    for video_info in node_out.get("videos", []):
                        filename = video_info.get("filename")
                        subfolder = video_info.get("subfolder", "")
                        if filename:
                            local_path = await self._download_output(
                                filename, subfolder, output_dir
                            )
                            logger.info(f"ComfyUI output downloaded: {local_path}")
                            return local_path
                    for gif_info in node_out.get("gifs", []):
                        filename = gif_info.get("filename")
                        subfolder = gif_info.get("subfolder", "")
                        if filename and filename.endswith(".mp4"):
                            local_path = await self._download_output(
                                filename, subfolder, output_dir
                            )
                            logger.info(f"ComfyUI output downloaded: {local_path}")
                            return local_path
            except ComfyUIError:
                raise
            except Exception as e:
                logger.debug(f"ComfyUI poll error (prompt {prompt_id}): {e}")

        raise ComfyUIError(
            f"ComfyUI workflow timed out after {timeout or self.timeout}s (prompt: {prompt_id})"
        )

    async def _download_output(self, filename: str, subfolder: str, dest_dir: str) -> str:
        """Download an output file from ComfyUI and save it locally."""
        params = {"filename": filename, "type": "output"}
        if subfolder:
            params["subfolder"] = subfolder
        local_path = os.path.join(dest_dir, filename)
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("GET", f"{self.base_url}/view", params=params) as resp:
                    if resp.status_code != 200:
                        raise ComfyUIError(
                            f"Failed to download output {filename}: HTTP {resp.status_code}"
                        )
                    with open(local_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(65536):
                            f.write(chunk)
        except ComfyUIError:
            raise
        except Exception as e:
            raise ComfyUIError(f"Output download failed: {e}")
        return local_path

    async def generate_t2v(
        self,
        prompt: str,
        negative_prompt: str,
        duration: int,
        width: int,
        height: int,
        fps: int,
        output_dir: str,
    ) -> str:
        """Text-to-Video using the wan_t2v.json workflow template."""
        template = _load_workflow("wan_t2v.json")
        params = {
            "PROMPT": prompt,
            "NEGATIVE_PROMPT": negative_prompt or "blurry, low quality, watermark, text",
            "DURATION": str(duration),
            "WIDTH": str(width),
            "HEIGHT": str(height),
            "FPS": str(fps),
            "FRAMES": str(duration * fps),
        }
        workflow = _fill_template(template, params)
        prompt_id = await self.submit_workflow(workflow)
        return await self.wait_for_output(prompt_id, output_dir)

    async def generate_i2v(
        self,
        prompt: str,
        negative_prompt: str,
        image_path: str,
        duration: int,
        width: int,
        height: int,
        fps: int,
        output_dir: str,
    ) -> str:
        """Image-to-Video using the wan_i2v.json workflow template."""
        server_image = await self.upload_image(image_path)
        template = _load_workflow("wan_i2v.json")
        params = {
            "PROMPT": prompt,
            "NEGATIVE_PROMPT": negative_prompt or "blurry, low quality, watermark, text",
            "IMAGE_FILENAME": server_image,
            "DURATION": str(duration),
            "WIDTH": str(width),
            "HEIGHT": str(height),
            "FPS": str(fps),
            "FRAMES": str(duration * fps),
        }
        workflow = _fill_template(template, params)
        prompt_id = await self.submit_workflow(workflow)
        return await self.wait_for_output(prompt_id, output_dir)


# Module-level singleton
_comfyui_client: Optional[ComfyUIClient] = None


def get_comfyui_client() -> ComfyUIClient:
    global _comfyui_client
    if _comfyui_client is None:
        _comfyui_client = ComfyUIClient()
    return _comfyui_client
