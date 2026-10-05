"""GPU and service availability diagnostics.

Runs at startup to log what is available. Never crashes the application —
all checks return warning strings instead of raising exceptions.
"""

import logging
import os
from typing import Any, Dict

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ── GPU (torch/CUDA) ─────────────────────────────────────────────────────────

async def check_gpu() -> Dict[str, Any]:
    """Detect CUDA GPU presence and VRAM.

    Returns a dict regardless of whether torch is installed.
    """
    result: Dict[str, Any] = {
        "available": False,
        "cuda": False,
        "gpu_name": None,
        "vram_gb": None,
        "warning": None,
    }
    try:
        import torch  # optional dependency
        result["cuda"] = torch.cuda.is_available()
        if result["cuda"]:
            result["available"] = True
            result["gpu_name"] = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            result["vram_gb"] = round(vram, 1)
            min_vram = get_settings().GPU_MIN_VRAM_GB
            if vram < min_vram:
                result["warning"] = (
                    f"GPU has {vram:.1f} GB VRAM, but {min_vram} GB is recommended. "
                    "Consider using WAN_MODE=t2v and WAN_MODEL_SIZE=1.3B (development mode)."
                )
                logger.warning(result["warning"])
            else:
                logger.info(f"GPU: {result['gpu_name']} — {result['vram_gb']} GB VRAM")
        else:
            result["warning"] = "No CUDA GPU detected. Wan2.1 video generation requires a GPU."
            logger.warning(result["warning"])
    except ImportError:
        result["warning"] = "torch not installed — GPU detection skipped. Install torch for GPU support."
        logger.info(result["warning"])
    except Exception as e:
        result["warning"] = f"GPU check error: {e}"
        logger.warning(result["warning"])
    return result


# ── Qwen3 / vLLM ────────────────────────────────────────────────────────────

async def check_qwen() -> Dict[str, Any]:
    """Ping the local vLLM Qwen3 server."""
    s = get_settings()
    result: Dict[str, Any] = {
        "available": False,
        "base_url": s.QWEN_BASE_URL,
        "model": s.QWEN_MODEL,
        "warning": None,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{s.QWEN_BASE_URL.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {s.QWEN_API_KEY or 'EMPTY'}"},
            )
        if resp.status_code == 200:
            result["available"] = True
            models = [m.get("id") for m in resp.json().get("data", [])]
            result["models"] = models
            logger.info(f"Qwen3 vLLM: available at {s.QWEN_BASE_URL} — models: {models}")
        else:
            result["warning"] = f"vLLM returned HTTP {resp.status_code}"
            logger.warning(f"Qwen3 vLLM: {result['warning']}")
    except httpx.ConnectError:
        result["warning"] = (
            f"Cannot connect to vLLM at {s.QWEN_BASE_URL}. "
            "Start with: vllm serve Qwen/Qwen3-8B --port 8000 --api-key EMPTY"
        )
        logger.info(f"Qwen3 vLLM not running — AI Director will use cloud LLM fallback")
    except Exception as e:
        result["warning"] = f"Qwen ping error: {e}"
        logger.warning(result["warning"])
    return result


# ── ComfyUI ──────────────────────────────────────────────────────────────────

async def check_comfyui() -> Dict[str, Any]:
    """Ping the local ComfyUI server."""
    s = get_settings()
    result: Dict[str, Any] = {
        "available": False,
        "base_url": s.COMFYUI_BASE_URL,
        "warning": None,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{s.COMFYUI_BASE_URL.rstrip('/')}/system_stats")
        if resp.status_code == 200:
            result["available"] = True
            data = resp.json()
            result["system"] = data.get("system", {})
            logger.info(f"ComfyUI: available at {s.COMFYUI_BASE_URL}")
        else:
            result["warning"] = f"ComfyUI returned HTTP {resp.status_code}"
    except httpx.ConnectError:
        result["warning"] = (
            f"Cannot connect to ComfyUI at {s.COMFYUI_BASE_URL}. "
            "Wan2.1 will fall back to direct CLI mode."
        )
        logger.info("ComfyUI not running — Wan will use direct CLI if configured")
    except Exception as e:
        result["warning"] = f"ComfyUI ping error: {e}"
    return result


# ── Wan2.1 model path ─────────────────────────────────────────────────────────

async def check_wan() -> Dict[str, Any]:
    """Check if the Wan2.1 model path exists locally."""
    s = get_settings()
    result: Dict[str, Any] = {
        "available": False,
        "mode": s.WAN_MODE,
        "model_size": s.WAN_MODEL_SIZE,
        "model_path": s.WAN_MODEL_PATH,
        "warning": None,
    }
    if not s.WAN_MODEL_PATH:
        result["warning"] = (
            "WAN_MODEL_PATH is not set. Wan2.1 direct CLI mode will not work. "
            "Set WAN_MODEL_PATH or ensure ComfyUI is running."
        )
        logger.info("WAN_MODEL_PATH not configured")
        return result

    if os.path.isdir(s.WAN_MODEL_PATH):
        result["available"] = True
        logger.info(f"Wan2.1 model found at {s.WAN_MODEL_PATH} (mode={s.WAN_MODE}, size={s.WAN_MODEL_SIZE})")
    else:
        result["warning"] = f"WAN_MODEL_PATH '{s.WAN_MODEL_PATH}' does not exist."
        logger.warning(result["warning"])
    return result


# ── Aggregated diagnostics ───────────────────────────────────────────────────

async def system_diagnostics() -> Dict[str, Any]:
    """Run all diagnostics concurrently and return aggregated results."""
    import asyncio
    gpu, qwen, comfyui, wan = await asyncio.gather(
        check_gpu(),
        check_qwen(),
        check_comfyui(),
        check_wan(),
    )
    diag = {
        "gpu": gpu,
        "qwen": qwen,
        "comfyui": comfyui,
        "wan": wan,
    }
    # Summary
    warnings = [
        v["warning"]
        for v in diag.values()
        if isinstance(v, dict) and v.get("warning")
    ]
    diag["warnings"] = warnings
    diag["video_engine_ready"] = comfyui["available"] or wan["available"]
    diag["llm_ready"] = qwen["available"]

    if warnings:
        logger.info(f"Startup diagnostics complete. {len(warnings)} warning(s).")
    else:
        logger.info("Startup diagnostics: all AI services nominal.")

    return diag
