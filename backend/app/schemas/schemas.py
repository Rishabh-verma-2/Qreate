"""Pydantic schemas for request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Projects ─────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    name: str
    topic: str
    description: Optional[str] = None
    status: str = "active"
    created_at: Any
    updated_at: Any


# ── Scripts ───────────────────────────────────────────────────────────────────

class SceneSchema(BaseModel):
    scene_number: int
    duration_seconds: int = 5
    narration: str = ""
    visual_description: str = ""
    camera_notes: str = ""
    visual_type: Optional[str] = None
    visual_subject: Optional[str] = None
    visual_action: Optional[str] = None
    visual_motion: Optional[str] = None
    transition: Optional[str] = None
    emphasis_words: Optional[List[str]] = None
    pacing: Optional[str] = None
    shot_type: Optional[str] = None


class ScriptGenerateRequest(BaseModel):
    project_id: str
    topic: str = Field(..., min_length=1, max_length=1000)
    title: Optional[str] = Field(None, max_length=200)
    duration_seconds: int = Field(60, ge=10, le=600)
    language: str = Field("English", max_length=50)
    tone: str = Field("professional", max_length=50)
    audience: str = Field("general", max_length=100)
    additional_instructions: Optional[str] = Field(None, max_length=1000)


class ScriptUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    hook: Optional[str] = Field(None, max_length=1000)
    closing: Optional[str] = Field(None, max_length=1000)
    scenes: Optional[List[SceneSchema]] = None
    approved: Optional[bool] = None


class ScriptResponse(BaseModel):
    id: str
    project_id: str
    title: str
    hook: Optional[str] = None
    closing: Optional[str] = None
    scenes: List[Any] = []
    language: str = "English"
    tone: str = "professional"
    duration_seconds: int = 60
    version: int = 1
    approved: bool = False
    created_at: Any
    updated_at: Any


# ── Video Generation ──────────────────────────────────────────────────────────

class VideoGenerateRequest(BaseModel):
    project_id: str
    script_id: str
    mode: str = Field("text", pattern="^(text|keyframe|reference)$")
    duration_seconds: int = Field(5, ge=4, le=12)
    aspect_ratio: str = Field("16:9", pattern="^(21:9|16:9|4:3|1:1|3:4|9:16)$")
    seed: Optional[int] = None
    use_full_script: bool = True
    engine: str = Field("auto", pattern="^(auto|free|agnes|purffle)$")



class VideoTaskResponse(BaseModel):
    id: str
    project_id: str
    script_id: str
    agnes_video_id: Optional[str] = None
    status: str  # pending | queued | in_progress | completed | failed
    progress: int = 0
    error_message: Optional[str] = None
    generation_settings: Dict[str, Any] = {}
    created_at: Any
    updated_at: Any
    completed_at: Optional[Any] = None


class GeneratedVideoResponse(BaseModel):
    id: str
    project_id: str
    script_id: Optional[str] = None
    task_id: Optional[str] = None
    cloudinary_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    original_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_format: str = "mp4"
    created_at: Any


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    cloudinary: str
    agnes: str
