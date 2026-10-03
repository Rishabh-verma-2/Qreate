"""Script generation service using Agnes 2.5 Flash."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)


SCRIPT_SYSTEM_PROMPT = """You are a world-class viral video director and master scriptwriter (creator of videos with 50M+ views across YouTube Shorts, Instagram Reels, and TikTok).

Your mission is to write HIGH-RETENTION, ADDICTIVE, and VISUALLY STUNNING video scripts that instantly grab viewers, keep their eyes glued to the screen, and make them watch until the final second.

Rules for Viral Scriptwriting:
1. EXPLOSIVE HOOK (First 2-3 Seconds):
   - Start immediately with a pattern-interrupt, shocking curiosity gap, or high-stakes statement.
   - FORBIDDEN OPENINGS: Never say "Welcome to", "Hello everyone", "In this video", "Today we will explore", "Have you ever wondered". Start directly in the heart of the action or mystery.
   - Example: "This machine costs thirty-eight million dollars, and only one person on Earth owns it."

2. RAPID-FIRE SCENE BREAKDOWN (3 to 5 Seconds per Scene):
   - Modern short-form video audiences lose attention if a background doesn't change every 3 to 5 seconds.
   - You MUST break the story down into tight, rapid-fire scenes:
     * For a 15-second video: Exactly 3 to 4 scenes.
     * For a 30-second video: Exactly 6 to 8 scenes.
     * For a 60-second video: Exactly 10 to 14 scenes.
   - Each scene should have a duration of 3 to 5 seconds.

3. CONCISE, HIGH-ENERGY NARRATION:
   - Keep narration to 10 to 18 words maximum per scene (about 3-4 seconds of speech).
   - Use punchy, conversational, and energetic phrasing.
   - Build momentum with suspense loops ("Wait until you see what happens next...", "And that is not even the craziest part...").

4. HYPER-SPECIFIC & UNIQUE VISUAL DESCRIPTIONS:
   - Every single scene MUST feature a completely distinct, brand-new visual subject so the background changes dramatically on every cut.
   - Be concrete and photographic: Name the specific subject, vehicle, model, landmark, object, material, lighting, and camera angle.
   - NEVER write vague filler like "a person talking", "a montage of clips", or "various scenes".
   - Good: "Cinematic low-angle close-up of a matte-black Bugatti Bolide exhaust pipe spitting blue nitrous flames on rain-slicked asphalt at night."

5. COMPELLING CALL TO ACTION:
   - Conclude with a strong, curiosity-driven question or high-energy call to action that sparks engagement and comments.

Always respond with valid JSON only — no markdown code blocks, no explanations outside the JSON.

The JSON must follow this exact structure:
{
  "title": "Viral Video Title",
  "total_duration_seconds": 30,
  "hook": "Explosive opening hook sentence to grab attention immediately",
  "closing": "Closing question or high-engagement CTA",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "narration": "Punchy, exciting spoken line (10-18 words maximum).",
      "visual_description": "Hyper-specific photorealistic visual naming concrete subjects, lighting, and camera perspective.",
      "camera_notes": "Camera angle or transition note (e.g. rapid zoom-in, low-angle tracking, sweeping pan)"
    }
  ]
}
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
    target_scenes = max(4, int(duration_seconds / 4.5))
    # If the user specifically asks for N facts, items, or tips, match scene count accordingly
    match = re.search(r'\b(\d+)\s+(facts|ways|reasons|tips|cars|things|secrets|hacks|steps|items)\b', f"{topic} {title or ''}", re.IGNORECASE)
    if match:
        list_count = int(match.group(1))
        target_scenes = max(target_scenes, min(list_count + 1, 12))
    prompt = f"""Generate a high-retention viral video script with the following parameters:

Topic: {topic}
{f'Title: {title}' if title else ''}
Target Total Duration: {duration_seconds} seconds
Required Scene Count: Approximately {target_scenes} distinct scenes (each 3 to 5 seconds)
Language: {language}
Tone: {tone} (high energy, engaging, captivating)
Target Audience: {audience}
{f'Additional Instructions: {additional_instructions}' if additional_instructions else ''}

CRITICAL:
- Divide into {target_scenes} scenes of 3-5 seconds each so backgrounds change rapidly and constantly!
- Each scene must have a unique, hyper-specific visual description naming exact subjects!
- Keep narration to 10-18 words per scene for rapid delivery!
- Output valid JSON only."""
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
