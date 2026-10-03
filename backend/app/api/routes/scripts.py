"""Script generation and management routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.database import crud
from app.schemas.schemas import ScriptGenerateRequest, ScriptUpdate
from app.services.research import gather_research
from app.services.script.generator import generate_script, script_fields_for_db

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=dict, status_code=201)
async def generate_new_script(body: ScriptGenerateRequest):
    """Generate a hook-first short-form script with the LLM provider chain."""
    # Verify project exists
    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {body.project_id}")

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
    )

    saved = await crud.create_script({
        "project_id": body.project_id,
        **script_fields_for_db(script_data),
        "language": body.language,
        "tone": body.tone,
        "audience": body.audience,
        "duration_seconds": body.duration_seconds,
        "original_prompt": body.topic,
        "additional_instructions": body.additional_instructions,
        "voice_gender": body.voice_gender,
        "user_media": [m.model_dump() for m in body.user_media],
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
