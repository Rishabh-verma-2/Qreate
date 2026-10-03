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
    duration_seconds: int = 4
    narration: str = ""
    visual_description: str = ""
    on_screen_text: str = ""
    search_queries: List[str] = []
    camera_notes: str = ""


class UserMedia(BaseModel):
    url: str = Field(..., max_length=1000)
    kind: str = Field("image", pattern="^(image|video)$")
    duration: Optional[float] = None


class ContentOptions(BaseModel):
    """Creative options shared by single, one-shot and batch generation."""
    title: Optional[str] = Field(None, max_length=200)
    voice_gender: str = Field("male", pattern="^(male|female)$")
    user_media: List[UserMedia] = Field(default_factory=list, max_length=30)
    duration_seconds: int = Field(30, ge=15, le=180)
    language: str = Field("English", max_length=50)
    tone: str = Field("energetic", max_length=50)
    audience: str = Field("general", max_length=100)
    additional_instructions: Optional[str] = Field(None, max_length=1000)


class ScriptGenerateRequest(ContentOptions):
    project_id: str
    topic: str = Field(..., min_length=1, max_length=1000)


class PipelineRunRequest(ContentOptions):
    """One-shot: topic in, publish-ready video out (script written by the worker)."""
    topic: str = Field(..., min_length=3, max_length=1000)


class BatchCreateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    topics: List[str] = Field(..., min_length=1)
    options: ContentOptions = ContentOptions()


class ScriptUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    hook: Optional[str] = Field(None, max_length=1000)
    hook_text: Optional[str] = Field(None, max_length=100)
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
    # Output is always vertical 1080x1920 for the Qoneqt feed; kept for API compatibility
    aspect_ratio: str = Field("9:16", pattern="^9:16$")



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
