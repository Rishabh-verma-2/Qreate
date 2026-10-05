"""AI Video Director API routes.

Provides endpoints for planning videos with local/custom Qwen3 LLM,
inspecting/editing video plans, and checking AI engine diagnostics.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.core.diagnostics import system_diagnostics
from app.database import crud
from app.schemas.schemas import VideoPlanRequest
from app.services.llm.video_director import QwenVideoDirector
from app.services.llm.schemas import Scene

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["AI Video Director"])


@router.post("/plan", status_code=status.HTTP_200_OK)
async def plan_video(body: VideoPlanRequest) -> Dict[str, Any]:
    """Generate a structured multi-scene VideoPlan using Qwen3 (or fallback).

    Fast and light: does NOT generate video or require GPU memory.
    """
    try:
        director = QwenVideoDirector()
        plan = await director.plan(
            prompt=body.prompt,
            style=body.style,
            duration=body.duration,
            aspect_ratio=body.aspect_ratio,
        )
        plan_dict = plan.model_dump()
        plan_id = await crud.save_video_plan(plan_dict, project_id=body.project_id)
        return {
            "plan_id": plan_id,
            "status": "completed",
            "plan": plan_dict,
        }
    except Exception as e:
        logger.error(f"Failed to generate video plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Video planning failed: {str(e)}",
        )


@router.get("/plan/{plan_id}", status_code=status.HTTP_200_OK)
async def get_video_plan(plan_id: str) -> Dict[str, Any]:
    """Retrieve an existing VideoPlan by plan_id."""
    plan = await crud.get_video_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video plan '{plan_id}' not found",
        )
    return {"plan_id": plan_id, "plan": plan}


@router.put("/plan/{plan_id}/scenes/{scene_id}", status_code=status.HTTP_200_OK)
async def update_scene_in_plan(
    plan_id: str, scene_id: str, scene_update: Dict[str, Any]
) -> Dict[str, Any]:
    """Update properties of a specific scene in a VideoPlan."""
    success = await crud.update_plan_scene(plan_id, scene_id, scene_update)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' in plan '{plan_id}' not found or update failed",
        )
    return {"message": "Scene updated successfully", "plan_id": plan_id, "scene_id": scene_id}


@router.get("/diagnostics", status_code=status.HTTP_200_OK)
async def get_diagnostics() -> Dict[str, Any]:
    """Return health/availability diagnostics for GPU, Qwen3, ComfyUI, and Wan2.1."""
    return await system_diagnostics()
