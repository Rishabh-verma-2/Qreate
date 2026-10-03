"""Script generator using Agnes 2.5 Flash and local Ollama (Qwen) LLM."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """You are a master viral video producer and educational content strategist.
Your task is to write engaging, high-retention video scripts broken down into concise, cinematic scenes.

CRITICAL ARCHITECTURE RULES:
1. Divide the script into dynamic, fast-paced scenes (typically 3–8 scenes depending on duration).
2. The first scene MUST contain an irresistible verbal and visual hook (first 3 seconds rule).
3. Every scene must have:
   - "scene_number": integer starting at 1
   - "duration_seconds": integer duration (3 to 10 seconds per scene)
   - "narration": punchy, conversational, active-voice voiceover text
   - "visual_description": vivid, cinematic visual description naming exact subjects, framing, and environment
   - "camera_notes": camera movements (e.g. "slow cinematic push-in", "dynamic whip pan", "orbit")
   - "visual_type": "cinematic" | "motion_graphic" | "diagram" | "photo"
   - "visual_subject": the primary object, phenomenon, or person on screen
   - "visual_action": what happens visually in this scene
   - "emphasis_words": list of 1-3 critical spoken words to highlight on screen
   - "concept_key": optional concept string if scene explains a known physical/technical process (e.g. "curved_spacetime", "wave_interference", "einstein_ring", "transformation", "physical_demo", "rf_carrier", "qam_constellation")

OUTPUT FORMAT:
Output MUST be strict, valid JSON with NO markdown formatting, NO conversational preamble, and NO extra text:
{
  "title": "Compelling Video Title",
  "hook": "Opening hook line designed to stop the scroll",
  "closing": "Memorable conclusion or call to action",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "narration": "...",
      "visual_description": "...",
      "camera_notes": "...",
      "visual_type": "cinematic",
      "visual_subject": "...",
      "visual_action": "...",
      "emphasis_words": ["word1", "word2"],
      "concept_key": null
    }
  ]
}
"""


def _build_user_prompt(
    topic: str,
    duration_seconds: int = 60,
    language: str = "English",
    tone: Union[str, List[str]] = "professional",
    audience: str = "general",
    title: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> str:
    # Multi-tone formatting
    if isinstance(tone, list):
        tone_instruction = f"Blend of {', '.join(tone)}"
    else:
        tone_instruction = tone

    target_words = int(duration_seconds * 2.3)
    num_scenes = max(3, min(12, int(duration_seconds / 6.0)))
    words_per_scene = max(8, int(target_words / num_scenes))

    prompt = f"""Generate a high-retention educational video script with the following parameters:

Topic: {topic}
{f'Title: {title}' if title else ''}
Target Duration: {duration_seconds} seconds (~{target_words} spoken words across {num_scenes} scenes)
Language: {language}
Tone: {tone_instruction}
Target Audience: {audience}
{f'Additional Instructions: {additional_instructions}' if additional_instructions else ''}

Generate exactly {num_scenes} cohesive, high-impact scenes.
Each scene's narration must have approximately {words_per_scene} spoken words with clear explanation so that Edge TTS voiceover totals ~{duration_seconds} seconds.
For EVERY scene, determine what the viewer must SEE to understand the narration, choose the composition archetype semantically, and choose a contextual background family. Output valid JSON only."""
    return prompt.strip()


def _parse_script_response(raw: str) -> Dict[str, Any]:
    """Parse LLM response into script dict with robust truncation recovery."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        cleaned = "\n".join(inner)

    parsed = None
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # If truncated by LLM token limit, repair by slicing at last valid scene boundary
        if not parsed:
            last_brace = cleaned.rfind('}')
            while last_brace > 0:
                candidate = cleaned[:last_brace + 1]
                for suffix in [']}', '}', '"]}', '"}]}']:
                    try:
                        test_parsed = json.loads(candidate + suffix)
                        if isinstance(test_parsed.get("scenes"), list) and len(test_parsed["scenes"]) > 0:
                            parsed = test_parsed
                            logger.info(f"Successfully repaired truncated JSON script with {len(parsed['scenes'])} scenes")
                            break
                    except Exception:
                        continue
                if parsed:
                    break
                last_brace = cleaned.rfind('}', 0, last_brace)

        if not parsed:
            raise AgnesAPIError(f"Could not parse script JSON: {e}", status_code=502)

    # Validate required fields
    if not isinstance(parsed.get("scenes"), list) or len(parsed["scenes"]) == 0:
        raise AgnesAPIError("Script response missing scenes array", status_code=502)

    # Normalize scene fields including enriched V3 visual intent metadata
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
        scene["concept_key"] = scene.get("concept_key")

        # V3 Universal Visual Storytelling Fields
        scene["core_claim"] = scene.get("core_claim") or scene.get("narration", "")[:60]
        scene["visual_goal"] = scene.get("visual_goal") or scene.get("visual_description", "")[:80]
        scene["composition"] = scene.get("composition") or "A_HERO_VISUAL"
        scene["animation_sequence"] = scene.get("animation_sequence") or [scene.get("visual_action", "")]
        scene["supporting_text"] = scene.get("supporting_text") or (scene.get("visual_subject", "")[:25].upper() if scene.get("visual_subject") else "")
        scene["transition_to_next"] = scene.get("transition_to_next") or "smooth_continuity"
        scene["background_family"] = scene.get("background_family") or "clean_studio"

    return parsed


async def _generate_via_ollama(messages: List[Dict[str, str]]) -> Optional[str]:
    """Attempt fast local script generation via Ollama (qwen2.5:7b)."""
    try:
        # Fast 1.0s connect timeout so if Ollama is down, we don't wait
        fast_timeout = httpx.Timeout(connect=1.0, read=30.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=fast_timeout) as http_client:
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
    tone: Union[str, List[str]] = "professional",
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
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."
    return prompt
