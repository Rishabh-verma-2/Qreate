"""Pydantic schemas for PurffleShorts script format."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PurffleScene(BaseModel):
    narration: str = Field(..., description="Spoken narration for the scene")
    search_query: str = Field(..., description="Stock footage search term (English)")
    image_prompt: str = Field(..., description="AI image generation prompt (English)")
    speaker: str = Field("A", description="Speaker ID ('A' or 'B')")


class PurffleScript(BaseModel):
    topic: str = Field(..., description="Video topic")
    title: str = Field(..., description="Shorts title")
    hook_text: str = Field(..., description="Opening title text shown in first seconds")
    scenes: List[PurffleScene] = Field(..., min_length=1, description="List of scenes")
    description: str = Field("", description="Video description")
    hashtags: List[str] = Field(default_factory=lambda: ["#shorts", "#education"], description="Hashtags")
    tags: List[str] = Field(default_factory=lambda: ["shorts", "facts", "education"], description="Search tags")
    category: str = Field("education", description="YouTube category name")
    style: str = Field("facts", description="Script style (facts, story, explainer, etc.)")
    language: str = Field("en", description="Language code")
    cast: List[str] = Field(default_factory=lambda: ["Narrator"], description="Speaker names")
