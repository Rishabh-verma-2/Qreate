"""Script generation and management routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.ratelimit import enforce

from app.database import crud
from app.schemas.schemas import ScriptGenerateRequest, ScriptUpdate, style_from
from app.services.research import gather_research
from app.services.script.generator import generate_script, regenerate_scene, script_fields_for_db

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=dict, status_code=201)
async def generate_new_script(body: ScriptGenerateRequest, request: Request):
    """Generate a hook-first short-form script with the LLM provider chain."""
    # Verify project exists or auto-create standalone project for custom video
    project_id = getattr(body, "project_id", None)
    project = None
    if project_id and project_id not in ("default", "custom", "none", ""):
        project = await crud.get_project(project_id)
    if not project:
        name = (getattr(body, "topic", None) or "Custom Video")[:60]
        project = await crud.create_project({
            "name": name,
            "topic": body.topic,
            "description": "Auto-created standalone project for custom video",
        })
        body.project_id = project["id"]

    owner = await enforce(request, "script")
    research = await gather_research(body.topic, body.language)
    script_data = await generate_script(
        research=research,
        topic=body.topic,
        duration_seconds=body.duration_seconds,
        language=body.language,
        tone=body.tone,
        audience=body.audience,
        title=body.title,
        additional_instructions=body.additional_instructions,
        has_user_media=bool(body.user_media),
        video_format=body.video_format,
        visual_style=body.visual_style,
        people_focus=body.people_focus,
    )

    saved = await crud.create_script({
        "project_id": body.project_id,
        "owner": owner,
        **script_fields_for_db(script_data),
        "language": body.language,
        "tone": body.tone,
        "audience": body.audience,
        "duration_seconds": body.duration_seconds,
        "original_prompt": body.topic,
        "additional_instructions": body.additional_instructions,
        "voice_gender": body.voice_gender,
        "user_media": [m.model_dump() for m in body.user_media],
        "style": style_from(body),
        "approved": False,
        "version": 1,
    })

    # Update project updated_at
    await crud.update_project(body.project_id, {})

    return {"data": saved, "message": "Script generated successfully"}


@router.post("/{script_id}/regenerate", response_model=dict)
async def regenerate_script(script_id: str):
    """Regenerate a script using the same parameters."""
    existing = await crud.get_script(script_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    script_data = await generate_script(
        topic=existing.get("original_prompt", ""),
        duration_seconds=existing.get("duration_seconds", 30),
        language=existing.get("language", "English"),
        tone=existing.get("tone", "professional"),
        audience=existing.get("audience", "general"),
        title=existing.get("title"),
        additional_instructions=existing.get("additional_instructions"),
        has_user_media=bool(existing.get("user_media")),
    )

    updated = await crud.update_script(script_id, {
        **script_fields_for_db(script_data),
        "approved": False,
        "version": (existing.get("version", 1) or 1) + 1,
    })

    return {"data": updated, "message": "Script regenerated"}


@router.get("/{script_id}", response_model=dict)
async def get_script(script_id: str):
    """Get a script by ID."""
    script = await crud.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
    return {"data": script}


@router.put("/{script_id}", response_model=dict)
async def update_script(script_id: str, body: ScriptUpdate):
    """Update script content."""
    existing = await crud.get_script(script_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    updates = body.model_dump(exclude_none=True)
    if "scenes" in updates:
        updates["scenes"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in body.scenes]

    updated = await crud.update_script(script_id, updates)
    return {"data": updated, "message": "Script updated"}


@router.post("/{script_id}/scenes/{scene_index}/regenerate", response_model=dict)
async def regenerate_one_scene(script_id: str, scene_index: int, body: Optional[dict] = None):
    """Rewrite a single scene (0-based index) and save it; returns the updated script."""
    existing = await crud.get_script(script_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
    scenes = list(existing.get("scenes") or [])
    if not 0 <= scene_index < len(scenes):
        raise HTTPException(status_code=422, detail="Scene index out of range")
    new_scene = await regenerate_scene(existing, scene_index, (body or {}).get("instructions"))
    scenes[scene_index] = {k: v for k, v in new_scene.items() if not k.startswith("_")}
    updated = await crud.update_script(script_id, {"scenes": scenes})
    return {"data": updated, "message": f"Scene {scene_index + 1} regenerated"}
