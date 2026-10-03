"""Script generation service using Agnes 2.5 Flash."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)


SCRIPT_SYSTEM_PROMPT = """You are a professional video scriptwriter. Generate structured video scripts in JSON format.

Always respond with valid JSON only — no markdown code blocks, no explanations outside the JSON.

The JSON must follow this exact structure:
{
  "title": "Video title",
  "total_duration_seconds": 60,
  "hook": "Opening hook sentence to grab attention",
  "closing": "Closing statement or call to action",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 10,
      "narration": "Narration text for this scene",
      "visual_description": "Detailed description of what should appear visually in this scene",
      "camera_notes": "Camera angle, movement, or transition notes (optional)"
    }
  ]
}

Requirements:
- Generate realistic scene durations that sum to approximately the total_duration_seconds
- Make narration natural and engaging for the specified tone and audience
- Keep visual descriptions concrete and actionable for video generation
- Number of scenes should match the video duration (roughly 1 scene per 10-15 seconds)
"""


def _build_user_prompt(
    topic: str,
    title: Optional[str],
    duration_seconds: int,
    language: str,
    tone: str,
    audience: str,
    additional_instructions: Optional[str],
) -> str:
    prompt = f"""Generate a video script with the following parameters:

Topic: {topic}
{f'Title: {title}' if title else ''}
Target Duration: {duration_seconds} seconds
Language: {language}
Tone: {tone}
Target Audience: {audience}
{f'Additional Instructions: {additional_instructions}' if additional_instructions else ''}

Generate a complete, structured script in JSON format as specified."""
    return prompt.strip()


def _parse_script_response(raw: str) -> Dict[str, Any]:
    """Parse Agnes response into script dict. Strip markdown fences if present."""
    # Remove markdown code blocks if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (the ``` fences)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        cleaned = "\n".join(inner)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Try to extract JSON from anywhere in the response
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                raise AgnesAPIError(f"Could not parse script JSON: {e}", status_code=502)
        else:
            raise AgnesAPIError(f"Agnes returned invalid JSON for script: {e}", status_code=502)

    # Validate required fields
    if not isinstance(parsed.get("scenes"), list) or len(parsed["scenes"]) == 0:
        raise AgnesAPIError("Script response missing scenes array", status_code=502)

    # Normalize scene fields
    for i, scene in enumerate(parsed["scenes"]):
        scene["scene_number"] = scene.get("scene_number", i + 1)
        scene["duration_seconds"] = scene.get("duration_seconds", 10)
        scene["narration"] = scene.get("narration", "")
        scene["visual_description"] = scene.get("visual_description", "")
        scene["camera_notes"] = scene.get("camera_notes", "")

    return parsed


async def generate_script(
    topic: str,
    duration_seconds: int = 60,
    language: str = "English",
    tone: str = "professional",
    audience: str = "general",
    title: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a video script using Agnes 2.5 Flash.

    Returns a structured script dict with title, hook, scenes, and closing.
    """
    client = get_agnes_client()
    user_prompt = _build_user_prompt(
        topic=topic,
        title=title,
        duration_seconds=duration_seconds,
        language=language,
        tone=tone,
        audience=audience,
        additional_instructions=additional_instructions,
    )

    messages = [
        {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    logger.info(f"Generating script: topic={topic!r} duration={duration_seconds}s tone={tone}")
    raw = await client.chat_completion(messages, temperature=0.8, max_tokens=4096)
    script = _parse_script_response(raw)
    logger.info(f"Script generated: {len(script.get('scenes', []))} scenes")
    return script


def script_to_video_prompt(script: Dict[str, Any]) -> str:
    """Flatten a structured script into a single video prompt for Agnes video API."""
    parts = []
    hook = script.get("hook", "")
    if hook:
        parts.append(hook)

    scenes: List[Dict] = script.get("scenes", [])
    for scene in scenes:
        visual = scene.get("visual_description", "").strip()
        narration = scene.get("narration", "").strip()
        if visual:
            parts.append(visual)
        elif narration:
            parts.append(narration)

    closing = script.get("closing", "")
    if closing:
        parts.append(closing)

    prompt = " ".join(parts)
    # Agnes video prompts work best under ~500 chars — truncate gracefully
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."
    return prompt
