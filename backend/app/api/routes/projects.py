"""Project routes."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.core.errors import NotFoundError
from app.database import crud
from app.schemas.schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["Projects"])
logger = logging.getLogger(__name__)


@router.post("", response_model=dict, status_code=201)
async def create_project(body: ProjectCreate):
    """Create a new video project."""
    project = await crud.create_project({
        "name": body.name,
        "topic": body.topic,
        "description": body.description,
        "status": "active",
    })
    return {"data": project, "message": "Project created"}


@router.get("", response_model=dict)
async def list_projects():
    """List all projects."""
    projects = await crud.list_projects(limit=100)
    return {"data": projects, "total": len(projects)}


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str):
    """Get project details including scripts and videos."""
    project = await crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    scripts = await crud.list_scripts_for_project(project_id)
    tasks = await crud.list_tasks_for_project(project_id)
    videos = await crud.list_videos_for_project(project_id)

    return {
        "data": {
            **project,
            "scripts": scripts,
            "video_tasks": tasks,
            "generated_videos": videos,
        }
    }


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project."""
    deleted = await crud.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
