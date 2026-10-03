"""Script generation service using Agnes 2.5 Flash."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)


SCRIPT_SYSTEM_PROMPT = """You are an elite short-form video scriptwriter and visual director. You create viral, visually intentional science and technology explainer shorts (YouTube Shorts, TikTok, Instagram Reels).

Always respond with valid JSON only — no markdown code blocks, no explanations outside the JSON.

The JSON must follow this exact structure:
{
  "title": "Compelling video title",
  "total_duration_seconds": 60,
  "hook": "Punchy opening hook sentence (2-4 seconds) that creates an irresistible visual or conceptual curiosity gap",
  "closing": "Memorable final takeaway or insight",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "narration": "What if I told you a black hole can bend light itself?",
      "visual_description": "Massive black hole with a glowing golden accretion disk in deep space, with distant stars visibly distorted around it",
      "camera_notes": "Slow cinematic push-in toward the black hole",
      "visual_type": "cinematic_space",
      "visual_subject": "black hole accretion disk",
      "visual_action": "light rays curve around the dark event horizon",
      "visual_motion": "slow_push_in",
      "transition": "hard_cut",
      "emphasis_words": ["black hole", "bend light"],
      "pacing": "fast",
      "shot_type": "wide_shot"
    }
  ]
}

Pacing & Storytelling Rules:
1. SCENE COUNT & PACING: For a 45-75 second Short, generate 8 to 12 meaningful visual scenes. Most scenes should be 3 to 7 seconds. Never generate long static 15-second scenes.
2. HOOK (Scene 1): The first 2-4 seconds must grab the viewer instantly. Use a surprising question, counterintuitive fact, or visual mystery.
3. CONVERSATIONAL NARRATION: Write natural, punchy sentences. Avoid academic jargon and passive voice. Use rhythm, natural pauses, and momentum.
4. VISUAL STORYTELLING: When an important concept changes, the visual must change with it. Each visual must explain or reinforce the narration, not serve as generic filler.
5. METADATA: Provide accurate visual_type, visual_subject, visual_action, visual_motion, transition, emphasis_words, pacing, and shot_type for every scene.
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
    prompt = f"""Generate a high-retention educational video script with the following parameters:

Topic: {topic}
{f'Title: {title}' if title else ''}
Target Duration: {duration_seconds} seconds
Language: {language}
Tone: {tone}
Target Audience: {audience}
{f'Additional Instructions: {additional_instructions}' if additional_instructions else ''}

Generate 8 to 12 fast-paced scenes. Output valid JSON only."""
    return prompt.strip()


def _parse_script_response(raw: str) -> Dict[str, Any]:
    """Parse LLM response into script dict. Strip markdown fences if present."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        cleaned = "\n".join(inner)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                raise AgnesAPIError(f"Could not parse script JSON: {e}", status_code=502)
        else:
            raise AgnesAPIError(f"LLM returned invalid JSON for script: {e}", status_code=502)

    # Validate required fields
    if not isinstance(parsed.get("scenes"), list) or len(parsed["scenes"]) == 0:
        raise AgnesAPIError("Script response missing scenes array", status_code=502)

    # Normalize scene fields including enriched V2 metadata
    for i, scene in enumerate(parsed["scenes"]):
        scene["scene_number"] = scene.get("scene_number", i + 1)
        scene["duration_seconds"] = scene.get("duration_seconds", 5)
        scene["narration"] = scene.get("narration", "")
        scene["visual_description"] = scene.get("visual_description", "")
        scene["camera_notes"] = scene.get("camera_notes", "")
        scene["visual_type"] = scene.get("visual_type", "cinematic")
        scene["visual_subject"] = scene.get("visual_subject", "")
        scene["visual_action"] = scene.get("visual_action", "")
        scene["visual_motion"] = scene.get("visual_motion", "slow_push_in")
        scene["transition"] = scene.get("transition", "hard_cut")
        scene["emphasis_words"] = scene.get("emphasis_words", [])
        scene["pacing"] = scene.get("pacing", "medium")
        scene["shot_type"] = scene.get("shot_type", "medium_shot")

    return parsed


async def _generate_via_ollama(messages: List[Dict[str, str]]) -> Optional[str]:
    """Attempt fast local script generation via Ollama (qwen2.5:7b)."""
    try:
        async with httpx.AsyncClient(timeout=45.0) as http_client:
            payload = {
                "model": "qwen2.5:7b",
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 2048},
            }
            resp = await http_client.post("http://localhost:11434/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content")
                if content:
                    logger.info("Generated script via local Ollama (qwen2.5:7b)")
                    return content
    except Exception as e:
        logger.info(f"Ollama local generator not used or unavailable ({e}); proceeding with cloud generator")
    return None


async def generate_script(
    topic: str,
    duration_seconds: int = 60,
    language: str = "English",
    tone: str = "professional",
    audience: str = "general",
    title: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a video script using Ollama (Qwen) if available, falling back to Agnes 2.5 Flash.

    Returns a structured script dict with title, hook, scenes, and closing.
    """
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

    # 1. Try local Ollama / Qwen first
    raw = await _generate_via_ollama(messages)

    # 2. Fall back to Agnes AI Cloud
    if not raw:
        client = get_agnes_client()
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
