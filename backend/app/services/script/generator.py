"""Script generation service using Agnes 2.5 Flash."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

import httpx
from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)


SCRIPT_SYSTEM_PROMPT = """You are an elite short-form video director and visual storyteller for PurffleShorts V3.
You create visually captivating, high-retention vertical explainers (YouTube Shorts, TikTok, Instagram Reels).

CORE PRINCIPLE: NARRATION MUST DRIVE THE VISUAL
The permanent rule is:
NARRATION → MEANING → VISUAL INTENT → VISUAL REPRESENTATION → COMPOSITION → ANIMATION → RENDER
(Never choose a generic flowchart or fixed template regardless of what the narration is actually saying.)

For EVERY scene, ask: "WHAT SHOULD THE VIEWER SEE IN ORDER TO UNDERSTAND WHAT IS BEING SAID?"
- If narration says "The engine provides thrust" → Show engine + exhaust vector + forward movement (Physical Demo). NOT a flowchart.
- If narration says "Heat melts the butter" → Show butter physically melting into liquid (Transformation). NOT Phase 1, Phase 2.
- If narration says "Compound interest accelerates balance growth" → Show balance curve bending sharply upward (Data Viz).
- If narration says "Gravity pulls downward" → Show object + downward gravitational force arrow (Physical Demo).
- If narration says "The packet reaches your phone" → Show packet traveling across space into phone (Object Interaction).

Always respond with valid JSON only — no markdown code blocks, no explanations outside the JSON.

The JSON must follow this exact structure:
{
  "title": "Compelling video title",
  "total_duration_seconds": 60,
  "hook": "Punchy opening hook sentence (2-4 seconds) creating an irresistible visual curiosity gap",
  "closing": "Memorable final insight",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "narration": "In flat spacetime, light travels in a perfectly straight line — always.",
      "core_claim": "Light follows straight paths in unwarped space",
      "visual_goal": "A photon beam travelling in a straight line from source to detector",
      "visual_subject": "photon beam",
      "visual_action": "light travels straight across Euclidean grid",
      "composition": "A_HERO_VISUAL",
      "animation_sequence": ["emitter pulses", "straight beam traverses grid", "receiver detects signal"],
      "supporting_text": "FLAT SPACE → STRAIGHT PATH",
      "transition_to_next": "space begins to bend around approaching mass",
      "background_family": "deep_space",
      "visual_type": "animated_diagram",
      "concept_key": "straight_light_ray",
      "visual_description": "Clean dark grid with glowing photon laser travelling in a straight path",
      "camera_notes": "Static frame with traveling light pulse",
      "emphasis_words": ["straight line", "flat spacetime"],
      "pacing": "fast",
      "shot_type": "wide_shot"
    }
  ]
}

COMPOSITION ARCHETYPES (Choose semantically based on what the narration is explaining):
- A_HERO_VISUAL: Large central subject with subtle motion, minimal text (establishing hero moments).
- B_PHYSICAL_DEMO: Objects move & interact with visible force vectors, velocity, thrust, or gravity.
- C_PROCESS: Step-by-step workflow (USE ONLY FOR GENUINE MULTI-STAGE PROCEDURES/SYSTEMS). Never default to this for physical action!
- D_TRANSFORMATION: One state visibly morphs or transitions into another (solid to liquid, raw to cooked, unencoded to encoded).
- E_COMPARISON: Two contrasting concepts shown side-by-side or stacked (e.g. 2.4 GHz vs 5 GHz, Newton vs Einstein).
- F_CLOSE_UP: Camera focuses deep into a specific component or internal mechanism.
- G_FULL_DIAGRAM: Full-screen annotated technical or scientific schematic.
- H_CINEMATIC: Real or sourced footage with minimal overlay (telescopes, real-world footage, hero discoveries).
- I_DATA_VIZ: Charts, metrics, numbers, or growth curves accelerating/growing over time.
- J_MAP_TIMELINE: Geographical route, historical evolution, or chronological milestone timeline.
- K_OBJECT_INTERACTION: Two or more objects interact, collide, or exchange signals/packets.
- L_COMBINED_SYSTEM: Coordinated multi-part system (used only when concept genuinely requires it).

BACKGROUND FAMILIES (Choose semantically to support the scene, NOT a generic dark wallpaper):
- clean_studio: Minimal, elegant neutral slate/charcoal studio vignette with soft lighting (products, general concepts)
- technical_engineering: Blueprint precision grid, subtle graphite markings (hardware, engines, physical systems)
- optical_lens: Radial optical aperture / glass refraction vignette (cameras, lenses, light, photons, imaging)
- microscopic_sensor: Silicon wafer micro-circuit / pixel sensor grid (sensors, semiconductors, chips, pixels)
- atmospheric_cinematic: Deep moody cinematic lighting with soft depth (moody real-world contexts)
- natural_organic: Deep warm amber/emerald organic gradients (cooking, biology, earth, nature)
- data_computational: Subtle digital matrix / network graph / processing raster (software, algorithms, image processing)
- deep_space: Cosmic starfield and dark nebula (ONLY for astronomy, relativity, cosmos, space)
- editorial_minimal: High contrast editorial graphite/ivory backdrop (finance, documents, metrics)

VISUAL DIVERSITY & CONTINUITY RULES:
1. DIVERSITY: Avoid using the exact same composition type or background across consecutive scenes.
2. CONTINUITY: The final visual state of Scene N should naturally lead into Scene N+1.
3. SUPPORTING TEXT: Short, bold semantic caption (2-4 words, e.g. "THRUST → FORWARD", "GRAVITY ↓", "LIGHT INTO SENSOR"). Never repetitive sentences.
4. TEXT MUST NEVER HIDE THE VISUAL: The visual carries the explanation; text merely reinforces it.
"""


def _format_tone_prompt(tone: Union[str, List[str]]) -> str:
    """Format single or multi-selected tones into a natural, meaningful instruction."""
    if isinstance(tone, list):
        clean = [str(t).strip().lower() for t in tone if str(t).strip()]
        if not clean:
            return "Use a professional tone."
        tone_str = ", ".join(clean)
        article = "an" if tone_str[0] in "aeiou" else "a"
        return f"Use {article} {tone_str} tone."
    elif isinstance(tone, str) and tone.strip():
        parts = [p.strip().lower() for p in tone.split(",") if p.strip()]
        if len(parts) > 1:
            tone_str = ", ".join(parts)
            article = "an" if tone_str[0] in "aeiou" else "a"
            return f"Use {article} {tone_str} tone."
        t_clean = tone.strip().lower()
        article = "an" if t_clean[0] in "aeiou" else "a"
        return f"Use {article} {t_clean} tone."
    return "Use a professional tone."


def _build_user_prompt(
    topic: str,
    title: Optional[str],
    duration_seconds: int,
    language: str,
    tone: Union[str, List[str]],
    audience: str,
    additional_instructions: Optional[str],
) -> str:
    target_words = int(duration_seconds * 2.2)
    # For a 90s video, 7-8 rich scenes is ideal (~11-13s per scene, ~25 words of narration)
    num_scenes = max(5, min(8, int(round(duration_seconds / 11.5))))
    words_per_scene = max(15, target_words // num_scenes)

    tone_instruction = _format_tone_prompt(tone)

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
        scene["duration_seconds"] = scene.get("duration_seconds", max(8, duration_seconds // len(parsed["scenes"]) if 'duration_seconds' in locals() else 8))
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
        # Fast 1.0s connect timeout so if Ollama is down, we don't wait 45s
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
    # Agnes video prompts work best under ~500 chars — truncate gracefully
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."
    return prompt
