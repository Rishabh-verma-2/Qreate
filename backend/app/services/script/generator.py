"""Script generator using Agnes 2.5 Flash (cloud) and local Ollama (Qwen) LLM.

Upgraded system prompt instructs the LLM to produce structured animation metadata
so that the motion_graphics engine can render concept-driven animated scenes instead
of falling back to Ken Burns on a stock photo for every scene.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.errors import AgnesAPIError
from app.services.agnes.client import get_agnes_client

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """You are a master animated video director and educational content architect.
Your task is to write high-retention animated video scripts broken into precise, cinematic scenes.

ANIMATION ARCHITECTURE RULES:
1. Every scene MUST have a concrete visual animation plan, not just a text description.
2. Divide the script into 4–8 scenes depending on duration.
3. The first scene MUST contain an irresistible hook (the "scroll-stopper").
4. For each scene, determine the precise COMPOSITION ARCHETYPE and assign CONCEPT_KEY.
5. For educational/science topics, MOST scenes should use animated diagrams — NOT photographs.

COMPOSITION ARCHETYPES (pick the best one for each scene):
- "PHYSICAL_DEMO": Objects move, interact, collide, or demonstrate forces/physics. Use for: gravity, motion, thrust, collisions, signals traveling, particles, etc.
- "TRANSFORMATION": A clear before → after state change. Use for: heating, melting, evolution, phase changes, before/after comparisons.
- "OBJECT_INTERACTION": Two or more objects exchanging data, signals, or energy. Use for: WiFi signals, data packets, router→phone, sender→receiver.
- "DATA_VIZ": Animated chart, graph, or metric. Use for: growth curves, statistics, comparisons, exponential functions.
- "MAP_TIMELINE": Chronological sequence or spatial journey. Use for: historical events, step-by-step workflows, processes with clear ordering.
- "HERO_VISUAL": A single concept dramatically visualized at center. Use for: introducing a subject, a "wow moment", a concept reveal.
- "COMPARISON": Side-by-side or before/after contrast. Use for: Newton vs Einstein, traditional vs modern, slow vs fast.
- "PROCESS_FLOW": Multi-step sequential process. Use for: how something works step-by-step, manufacturing, ordering pipeline.

CONCEPT_KEY REGISTRY — Use these exact strings when applicable:
Physics/Space: "straight_light_ray", "spacetime_curvature", "light_bending", "einstein_ring", "scale_comparison"
Signals/Networks: "radio_waves", "binary_packets", "frequency_spectrum", "object_interaction"
Data/Metrics: "data_viz", "data_metric", "map_timeline"
Universal: "hero_visual", "physical_demo", "transformation", "comparison", "process_visualization"
Generic fallback: "hero_visual"

SCENE REQUIREMENTS:
Each scene MUST contain ALL of these fields:
- "scene_number": integer starting at 1
- "duration_seconds": integer 3–10
- "narration": punchy, conversational, active-voice voiceover text (~spoken at 2.3 words/sec)
- "visual_description": specific visual content for the animation
- "camera_notes": camera movement hint
- "visual_type": "animated_diagram" | "motion_graphic" | "physical_simulation" | "data_visualization" | "cinematic_photo" | "process_diagram"
- "visual_subject": the primary object or concept being shown
- "visual_action": EXACTLY what moves/changes/animates in this scene
- "composition": one of the COMPOSITION ARCHETYPES above (use the exact string)
- "concept_key": one of the CONCEPT_KEY values above
- "core_claim": the single most important idea this scene communicates (max 60 chars)
- "animation_sequence": array of 2–4 strings describing the sequential animation steps
- "emphasis_words": list of 1–3 words to highlight on screen
- "background_family": "clean_studio" | "deep_space" | "technical_engineering" | "data_computational" | "natural_organic" | "optical_lens" | "microscopic_sensor" | "editorial_minimal"
- "supporting_text": short label/tag for the visual (max 25 chars, all caps)

SCIENCE/EDUCATION TOPICS: Use animated_diagram for 80%+ of scenes. Use concept_keys from the registry. Explain visually — don't just narrate over a photo.

CORPORATE/EVENT TOPICS: Use hero_visual, map_timeline, and process_diagram. Show locations, dates, schedules, speakers.

BUSINESS/PRODUCT TOPICS: Use transformation, data_viz, and process_visualization to show value.

OUTPUT FORMAT:
Output MUST be strict valid JSON with NO markdown, NO preamble, NO extra text:
{
  "title": "Compelling Video Title",
  "hook": "Opening hook line to stop the scroll",
  "closing": "Memorable conclusion or call to action",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 5,
      "narration": "...",
      "visual_description": "Animated diagram showing...",
      "camera_notes": "slow cinematic push-in",
      "visual_type": "animated_diagram",
      "visual_subject": "...",
      "visual_action": "...",
      "composition": "PHYSICAL_DEMO",
      "concept_key": "physical_demo",
      "core_claim": "...",
      "animation_sequence": ["Step 1 of animation", "Step 2", "Step 3"],
      "emphasis_words": ["word1", "word2"],
      "background_family": "deep_space",
      "supporting_text": "CORE CONCEPT"
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
    if isinstance(tone, list):
        tone_instruction = f"Blend of {', '.join(tone)}"
    else:
        tone_instruction = tone

    target_words = int(duration_seconds * 2.3)
    num_scenes = max(3, min(10, int(duration_seconds / 6.5)))
    words_per_scene = max(10, int(target_words / num_scenes))

    # Semantic guidance based on topic type
    topic_lower = topic.lower()
    is_science = any(w in topic_lower for w in ["physics", "space", "black hole", "gravity", "light", "quantum", "atom", "molecule", "biology", "chemistry", "astronomy", "star", "galaxy", "photon"])
    is_tech = any(w in topic_lower for w in ["wifi", "internet", "network", "signal", "router", "data", "algorithm", "ai", "software", "code", "computer", "digital"])
    is_event = any(w in topic_lower for w in ["summit", "conference", "event", "launch", "exhibition", "festival", "meetup", "seminar", "workshop"])
    is_business = any(w in topic_lower for w in ["business", "startup", "product", "company", "market", "investment", "revenue", "growth", "ecommerce", "saas"])
    is_process = any(w in topic_lower for w in ["how", "works", "process", "step", "order", "delivery", "workflow", "pipeline"])

    if is_science:
        visual_guidance = (
            "This is a SCIENCE topic. Use animated_diagram for 90%+ of scenes. "
            "Each scene MUST animate a physical process, not show a photograph. "
            "Use concept_keys: straight_light_ray, spacetime_curvature, light_bending, einstein_ring, "
            "physical_demo, transformation, scale_comparison, hero_visual."
        )
    elif is_tech:
        visual_guidance = (
            "This is a TECHNOLOGY topic. Visualize data packets, signals, radio waves, and system components. "
            "Use concept_keys: radio_waves, binary_packets, object_interaction, process_visualization, hero_visual."
        )
    elif is_event:
        visual_guidance = (
            "This is an EVENT PROMOTION. Use animated title reveals, location visuals, date/time animations, "
            "and a strong call to action. Use concept_keys: hero_visual, map_timeline, process_visualization."
        )
    elif is_business or is_process:
        visual_guidance = (
            "This is a BUSINESS/PROCESS topic. Show step-by-step workflows, animated metrics, and before/after states. "
            "Use concept_keys: process_visualization, data_viz, transformation, map_timeline, object_interaction."
        )
    else:
        visual_guidance = (
            "Choose the most visually descriptive composition for each scene. "
            "Prefer animated_diagram over cinematic_photo whenever the content can be illustrated."
        )

    prompt = f"""Generate a high-retention animated video script with these parameters:

Topic: {topic}
{f'Title: {title}' if title else ''}
Target Duration: {duration_seconds} seconds (~{target_words} spoken words across {num_scenes} scenes)
Language: {language}
Tone: {tone_instruction}
Target Audience: {audience}
{f'Additional Instructions: {additional_instructions}' if additional_instructions else ''}

VISUAL GUIDANCE FOR THIS TOPIC:
{visual_guidance}

Generate exactly {num_scenes} scenes.
Each scene narration: ~{words_per_scene} words spoken naturally at 2.3 words/second.
For EVERY scene, assign the most specific concept_key and composition that explains what the viewer will SEE animated.
Scenes should BUILD on each other — tell a visual story, not independent slides.
Output valid JSON only."""
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

        if not parsed:
            last_brace = cleaned.rfind('}')
            while last_brace > 0:
                candidate = cleaned[:last_brace + 1]
                for suffix in [']}', '}', '"]}', '"}]}']:
                    try:
                        test_parsed = json.loads(candidate + suffix)
                        if isinstance(test_parsed.get("scenes"), list) and len(test_parsed["scenes"]) > 0:
                            parsed = test_parsed
                            logger.info(f"Repaired truncated JSON: {len(parsed['scenes'])} scenes")
                            break
                    except Exception:
                        continue
                if parsed:
                    break
                last_brace = cleaned.rfind('}', 0, last_brace)

        if not parsed:
            raise AgnesAPIError(f"Could not parse script JSON: {e}", status_code=502)

    if not isinstance(parsed.get("scenes"), list) or len(parsed["scenes"]) == 0:
        raise AgnesAPIError("Script response missing scenes array", status_code=502)

    # Normalize and enrich scene fields
    for i, scene in enumerate(parsed["scenes"]):
        scene["scene_number"] = scene.get("scene_number", i + 1)
        scene["duration_seconds"] = scene.get("duration_seconds", 5)
        scene["narration"] = scene.get("narration", "")
        scene["visual_description"] = scene.get("visual_description", "")
        scene["camera_notes"] = scene.get("camera_notes", "")
        scene["visual_type"] = scene.get("visual_type", "animated_diagram")
        scene["visual_subject"] = scene.get("visual_subject", "")
        scene["visual_action"] = scene.get("visual_action", "")
        scene["visual_motion"] = scene.get("visual_motion", "slow_push_in")
        scene["transition"] = scene.get("transition", "hard_cut")
        scene["emphasis_words"] = scene.get("emphasis_words", [])
        scene["pacing"] = scene.get("pacing", "medium")
        scene["shot_type"] = scene.get("shot_type", "medium_shot")

        # Animation metadata (upgraded)
        scene["concept_key"] = scene.get("concept_key") or None
        scene["composition"] = scene.get("composition") or "HERO_VISUAL"
        scene["core_claim"] = scene.get("core_claim") or scene.get("narration", "")[:60]
        scene["visual_goal"] = scene.get("visual_goal") or scene.get("visual_description", "")[:80]
        scene["animation_sequence"] = scene.get("animation_sequence") or [scene.get("visual_action", "")]
        scene["supporting_text"] = scene.get("supporting_text") or (
            scene.get("visual_subject", "")[:25].upper() if scene.get("visual_subject") else "KEY CONCEPT"
        )
        scene["transition_to_next"] = scene.get("transition_to_next") or "smooth_continuity"
        scene["background_family"] = scene.get("background_family") or "clean_studio"

    return parsed


async def _generate_via_ollama(messages: List[Dict[str, str]]) -> Optional[str]:
    """Attempt fast local script generation via Ollama (qwen2.5:7b)."""
    try:
        fast_timeout = httpx.Timeout(connect=1.0, read=30.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=fast_timeout) as http_client:
            payload = {
                "model": "qwen2.5:7b",
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 3000},
            }
            resp = await http_client.post("http://localhost:11434/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content")
                if content:
                    logger.info("Generated script via local Ollama (qwen2.5:7b)")
                    return content
    except Exception as e:
        logger.info(f"Ollama not available ({e}); using Agnes cloud")
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
    """Generate a structured animation-ready video script.

    Uses Ollama (Qwen) locally if available, falls back to Agnes 2.5 Flash.
    Returns structured script dict with per-scene animation metadata.
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

    logger.info(f"Generating animation-ready script: topic={topic!r} duration={duration_seconds}s")

    raw = await _generate_via_ollama(messages)

    if not raw:
        client = get_agnes_client()
        raw = await client.chat_completion(messages, temperature=0.75, max_tokens=4096)

    script = _parse_script_response(raw)
    scenes = script.get("scenes", [])

    # Count how many scenes have explicit concept_keys
    keyed = sum(1 for s in scenes if s.get("concept_key"))
    logger.info(f"Script generated: {len(scenes)} scenes, {keyed} with concept_keys")
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
