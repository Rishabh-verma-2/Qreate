"""Pydantic schemas for PurffleShorts script format."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PurffleScene(BaseModel):
    narration: str = Field(..., description="Spoken narration for the scene")
    search_query: str = Field(..., description="Stock footage search term (English)")
    image_prompt: str = Field(..., description="AI image generation prompt (English)")
    speaker: str = Field("A", description="Speaker ID ('A' or 'B')")
    visual_type: Optional[str] = Field(None, description="Visual treatment type")
    concept_key: Optional[str] = Field(None, description="Motion graphics concept key")
    core_claim: Optional[str] = Field(None, description="Core claim/idea communicated by the narration")
    visual_goal: Optional[str] = Field(None, description="What the viewer should see to understand the claim")
    visual_subject: Optional[str] = Field(None, description="Primary visual subject or object")
    visual_action: Optional[str] = Field(None, description="Physical motion, vector force, or state change")
    composition: Optional[str] = Field(None, description="Composition archetype (A through L)")
    animation_sequence: Optional[List[str]] = Field(default_factory=list, description="Sequence of visual motion actions")
    supporting_text: Optional[str] = Field(None, description="Short semantic caption reinforcing visual")
    transition_to_next: Optional[str] = Field(None, description="Continuity bridge to next scene")
    background_family: Optional[str] = Field(None, description="Contextual environment/background family")


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
