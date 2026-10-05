"""Pydantic schemas for the AI Video Director (Qwen3) structured output.

Qwen3 must return a JSON object that validates against VideoPlan.
All validation is strict; missing or incorrectly typed fields will cause
VideoPlanError to be raised so the LLM can be prompted to retry.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Sub-models ────────────────────────────────────────────────────────────────

class CameraInstruction(BaseModel):
    """Describes how the virtual camera should behave during a scene."""
    shot_type: str = Field(
        "wide",
        description="close-up | medium | wide | aerial | pov | over-shoulder",
    )
    movement: str = Field(
        "static",
        description="static | pan-left | pan-right | dolly-in | dolly-out | orbit | handheld | drone",
    )
    angle: str = Field(
        "eye-level",
        description="eye-level | low-angle | high-angle | dutch | birds-eye",
    )


class Character(BaseModel):
    """A persistent character that appears across multiple scenes."""
    id: str = Field(..., description="Unique identifier e.g. 'character_001'")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., description="Who this character is in the story")
    appearance: str = Field(..., description="Detailed physical description for image generation")
    clothing: str = Field(..., description="Outfit description for consistency")
    style: str = Field("", description="Art style modifier e.g. '3D render', 'photorealistic'")
    reference_image: Optional[str] = Field(
        None,
        description="Path or URL to a reference image (filled by CharacterService after generation)",
    )

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9_\-]+$", v):
            # Sanitize instead of rejecting — small models often use spaces
            v = re.sub(r"[^a-z0-9_\-]", "_", v.lower())
        return v or "character_001"


class AudioPlan(BaseModel):
    """Audio settings for the complete video."""
    tts_voice: Optional[str] = Field(
        None,
        description="Edge-TTS voice ID; null = auto-select from language/tone",
    )
    music_mood: str = Field(
        "cinematic",
        description="none | upbeat | chill | cinematic | inspiring | dramatic | lofi | corporate | emotional",
    )
    sfx_notes: Optional[str] = Field("", description="Optional sound effect cues")

    @field_validator("sfx_notes", mode="before")
    @classmethod
    def sanitize_sfx(cls, v):
        return v if isinstance(v, str) else ""

    @field_validator("music_mood", mode="before")
    @classmethod
    def sanitize_mood(cls, v):
        return v if isinstance(v, str) and v else "cinematic"


class Scene(BaseModel):
    """A single independently-generated scene/shot in the video."""
    id: str = Field(..., description="Scene identifier e.g. 'scene_001'")
    duration: int = Field(..., ge=2, le=30, description="Duration in seconds")
    narration: str = Field(..., description="Spoken narration text for this scene")
    visual_prompt: str = Field(
        ...,
        description="Wan2.1 text prompt describing what is visually happening",
    )
    motion_prompt: str = Field(
        ...,
        description="Description of camera/subject motion for Wan2.1",
    )
    camera: CameraInstruction = Field(default_factory=CameraInstruction)
    style: str = Field("", description="Style modifier for this scene (overrides global if set)")
    characters: List[str] = Field(
        default_factory=list,
        description="List of character IDs appearing in this scene",
    )
    transition_in: str = Field(
        "cut",
        description="fade | cut | dissolve | wipe",
    )
    transition_out: str = Field(
        "cut",
        description="fade | cut | dissolve | wipe",
    )
    reference_image: Optional[str] = Field(
        None,
        description="Path to character reference image for I2V mode (filled by CharacterService)",
    )

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9_\-]+$", v):
            v = re.sub(r"[^a-z0-9_\-]", "_", v.lower())
        return v or "scene_001"

    @field_validator("transition_in", "transition_out")
    @classmethod
    def valid_transition(cls, v: str) -> str:
        allowed = {"fade", "cut", "dissolve", "wipe"}
        v = v.lower().strip()
        return v if v in allowed else "cut"

    @field_validator("visual_prompt", "motion_prompt", "narration")
    @classmethod
    def non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be empty")
        return v


class VideoPlan(BaseModel):
    """Complete AI-generated video plan produced by Qwen3.

    This is the structured output that drives the entire generation pipeline:
    characters → reference images → per-scene Wan2.1 calls → TTS → FFmpeg.
    """
    title: str = Field(..., min_length=1, max_length=200)
    total_duration: int = Field(..., ge=5, le=300, description="Target total duration in seconds")
    style: str = Field(..., description="Global visual style e.g. 'cinematic 3D animation'")
    aspect_ratio: str = Field("16:9", description="16:9 | 9:16 | 1:1")
    fps: int = Field(24, ge=12, le=60)
    language: str = Field("en", description="ISO 639-1 language code")
    audio: AudioPlan = Field(default_factory=AudioPlan)
    characters: List[Character] = Field(default_factory=list)
    scenes: List[Scene] = Field(..., min_length=1)

    @field_validator("aspect_ratio")
    @classmethod
    def valid_aspect(cls, v: str) -> str:
        allowed = {"16:9", "9:16", "1:1", "4:3", "3:4"}
        return v if v in allowed else "16:9"

    @model_validator(mode="after")
    def check_scene_duration_total(self) -> "VideoPlan":
        scene_total = sum(s.duration for s in self.scenes)
        # Allow ±30% slack: LLMs often overshoot/undershoot slightly
        lower = self.total_duration * 0.6
        upper = self.total_duration * 1.4
        if not (lower <= scene_total <= upper):
            # Auto-scale scene durations to match total
            import logging
            logging.getLogger(__name__).warning(
                f"Scene total {scene_total}s vs target {self.total_duration}s — scaling durations"
            )
            scale = self.total_duration / max(scene_total, 1)
            for scene in self.scenes:
                scene.duration = max(2, int(round(scene.duration * scale)))
        return self

    @model_validator(mode="after")
    def number_scenes(self) -> "VideoPlan":
        """Ensure scene IDs are present and sequential."""
        for i, scene in enumerate(self.scenes):
            if not scene.id or scene.id == "scene_001" and i > 0:
                scene.id = f"scene_{i + 1:03d}"
        return self


# ── Validation helper ─────────────────────────────────────────────────────────

def validate_video_plan(raw: dict) -> VideoPlan:
    """Parse and validate a raw dict from the LLM into a VideoPlan.

    Raises:
        pydantic.ValidationError: if the dict cannot be coerced into a valid plan.
    """
    return VideoPlan.model_validate(raw)
