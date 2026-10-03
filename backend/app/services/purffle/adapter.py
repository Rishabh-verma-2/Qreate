"""Adapter module: transforms Qreate structured scripts into Purffle-compatible scripts."""

import re
from typing import Any, Dict, List, Optional
from app.services.purffle.schemas import PurffleScene, PurffleScript


def _clean_search_query(text: str, fallback_topic: str) -> str:
    """Extract a concise, filmable stock footage query (1-4 words) from visual description."""
    if not text:
        return fallback_topic[:30].strip()
    
    # Remove camera notes, stage directions, and filler words
    cleaned = re.sub(
        r"\b(cut to|close-up|closeup|wide shot|medium shot|slow dolly|camera angle|view of|animation of|split-screen|animated view|showing a|smooth transition|quick cut)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    words = [w for w in cleaned.split() if len(w) > 2][:4]
    if words:
        return " ".join(words)
    return fallback_topic[:30].strip() or "cinematic background"


def _clean_image_prompt(visual_description: str, narration: str) -> str:
    """Create a vivid image generation prompt from visual description."""
    base = (visual_description.strip() or narration.strip() or "Cinematic scene").strip()
    # Strip camera direction prefixes
    base = re.sub(
        r"^(cut to|close-up shot of|close-up of|medium shot of|wide shot of|animation of|view of)\s*",
        "",
        base,
        flags=re.IGNORECASE,
    ).strip()
    return base


def qreate_script_to_purffle(script_data: Dict[str, Any], topic: Optional[str] = None) -> Dict[str, Any]:
    """Convert a Qreate structured script dictionary into Purffle-compatible JSON data.

    Args:
        script_data: Qreate script dictionary containing title, hook, closing, scenes.
        topic: Optional topic override if not present in script_data.

    Returns:
        Dictionary conforming to PurffleScript schema.
    """
    raw_topic = str(script_data.get("original_prompt") or topic or script_data.get("title") or "Shorts Explainer").strip()
    title = str(script_data.get("title") or raw_topic).strip()
    
    # Hook text for the first few seconds of video overlay
    raw_hook = str(script_data.get("hook") or title).strip()
    # Purffle displays hook_text in bold uppercase; truncate to punchy phrase
    clean_hook = re.sub(r"[^\w\s?!]", "", raw_hook).strip()
    hook_words = clean_hook.split()[:6]
    hook_text = " ".join(hook_words).upper() if hook_words else title[:30].upper()

    raw_scenes: List[Dict[str, Any]] = script_data.get("scenes") or []
    if not raw_scenes:
        # Fallback single scene if script is empty
        narration = str(script_data.get("hook") or title or "Video overview").strip()
        raw_scenes = [{
            "scene_number": 1,
            "narration": narration,
            "visual_description": title,
        }]

    purffle_scenes: List[PurffleScene] = []
    closing = str(script_data.get("closing") or "").strip()

    for i, scene in enumerate(raw_scenes):
        narration = str(scene.get("narration") or "").strip()
        visual_desc = str(scene.get("visual_description") or "").strip()
        
        # If this is the last scene and closing text exists, blend closing if not already present
        if i == len(raw_scenes) - 1 and closing and closing.lower() not in narration.lower():
            narration = f"{narration} {closing}".strip()

        search_query = _clean_search_query(visual_desc, raw_topic)
        image_prompt = _clean_image_prompt(visual_desc, narration)

        purffle_scenes.append(PurffleScene(
            narration=narration,
            search_query=search_query,
            image_prompt=image_prompt,
            speaker="A",
        ))

    description = f"{title}\n\n{raw_hook}"
    if closing:
        description += f"\n\n{closing}"

    purffle_script = PurffleScript(
        topic=raw_topic,
        title=title,
        hook_text=hook_text,
        scenes=purffle_scenes,
        description=description,
        hashtags=["#shorts", "#education", "#facts"],
        tags=["shorts", "facts", "education", raw_topic[:30].strip()],
        category="education",
        style="facts",
        language="en",
        cast=["Narrator"],
    )

    return purffle_script.model_dump()
