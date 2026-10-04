"""Script generation: topic → hook + story + scene plan + post copy + animation metadata.

Combines a two-pass creator workflow (writer + editor) with structured animation metadata
so scripts seamlessly power both:
  1. PurffleShorts V3 — 100% procedural animated motion graphics diagrams & explainers
  2. Qreate Reel Pipeline — dynamic real-footage stock b-roll & creator stories
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm import LLMError, generate_json
from app.services.research import research_brief

logger = logging.getLogger(__name__)

MUSIC_MOODS = ["upbeat", "chill", "cinematic", "inspiring", "dramatic", "lofi", "corporate", "emotional"]

# Phrases that instantly make a script read as machine-written.
AI_CLICHES = [
    "delve", "dive in", "dive into", "let's dive", "game-changer", "game changer", "unlock", "unleash",
    "in today's world", "in today's fast", "fast-paced world", "embark", "journey of", "testament to",
    "elevate your", "realm", "tapestry", "revolutionize", "seamless", "whether you're", "look no further",
    "buckle up", "ever wondered", "have you ever wondered", "in this video", "stay tuned", "without further ado",
    "it's important to note", "in conclusion", "navigate the", "harness the power", "the world of",
]

LANGUAGE_RULES = {
    "english": "Narration in natural spoken English.",
    "hindi": (
        "Narration in everyday spoken Hindi written in DEVANAGARI script (like a Delhi/Mumbai creator talks — "
        "not formal 'shuddh' Hindi; common English words like phone, office, Instagram are fine in Devanagari)."
    ),
    "hinglish": (
        "Narration in Hinglish written in ROMAN script, the way young Indians text and talk "
        "(e.g. 'Yaar, ye cheez koi nahi batata'). Mix Hindi and English naturally."
    ),
}

FORMATS = """- STORY: a mini narrative with a turn ("I tried X for 30 days…", a real-feeling moment, a twist).
- MYTH-BUST: "Everyone thinks X. It's actually Y." then proof.
- LIST/COUNTDOWN: 3 tight, specific items, best one last.
- HOW-TO: problem → 3 concrete steps → result.
- POV / RELATABLE: "POV: you…" describing a shared everyday moment, then the insight.
- BEFORE/AFTER or COMPARISON: contrast that makes the point visual.
- PERSONAL / EVENT (weddings, birthdays, trips, launches): warm first-person storytelling ("we", "our"),
  a few vivid specific moments, an emotional last line."""

WRITER_PROMPT = f"""You are a top short-form creator, animated video director, and head writer for Qoneqt, a community-first social app (Reddit meets Reels). You have studied thousands of viral Reels, YouTube Shorts, and animated explainers. You write scripts people watch to the end, rewatch, and comment on.

Think like a creator, not a narrator: you are talking TO one person, like a smart friend sharing something they can't wait to tell.

STEP 1 — pick the angle. Choose the ONE format that fits the topic best:
{FORMATS}

STEP 2 — the hook (first 3 seconds decide everything). Draft 3 different hooks, then choose the one that creates the strongest curiosity gap or emotion. Good hooks: a specific surprising claim, a bold opinion, a direct "you" callout, a relatable pain, or an open loop the video promises to close. Max 12 words. No greetings, no "Did you know", no "In this video".

STEP 3 — write for the ear:
- Short lines. Vary rhythm: a punchy 3-word line, then a longer one. Contractions. Rhetorical questions.
- Specific beats vague: real numbers, names of places/things, sensory details. Never generic filler.
- Re-hook every 2-3 scenes with a turn ("But here's the part nobody mentions…", "And then it got weird.").
- Deliver a real payoff. End with a line that makes people comment (a question or a "tag someone who…") or loops back to the hook.
- Punctuation is for the voice actor: commas and full stops create natural pauses; "…" for suspense.
- Banned (sounds AI-written): {", ".join(AI_CLICHES[:18])}, emojis, hashtags in narration, stage directions.

USING RESEARCH (when a RESEARCH block is provided):
- Build the angle around what people actually search and what's working in top Shorts — but write an original hook, never copy a title.
- Use concrete facts/numbers from the news items. Do NOT invent statistics; if you use a number it must come from the research or be common knowledge.
- Tie in a trending-today topic only if it genuinely connects.

STEP 4 — visuals & animation plan.
Each scene gets:
- 2 stock-footage search queries of 2-4 words: concrete subject + action/setting that a stock site really has ("woman sipping chai balcony", "hands typing laptop night").
- 1-4 words of on_screen_text that capture the scene's key point (a number, a keyword).
- An animation COMPOSITION ARCHETYPE & CONCEPT_KEY for procedural motion graphics:
  - "PHYSICAL_DEMO" (concept_key: "physical_demo"): Objects move, collide, fall, or demonstrate physical forces/speed.
  - "TRANSFORMATION" (concept_key: "transformation"): Before → after state change, melting, cooling, heating.
  - "OBJECT_INTERACTION" (concept_key: "object_interaction"): Two devices/objects exchanging signals, packets, radio waves.
  - "DATA_VIZ" (concept_key: "data_viz"): Animated growth chart, metric card, balance comparison.
  - "MAP_TIMELINE" (concept_key: "map_timeline"): Chronology, milestones, step progression.
  - "HERO_VISUAL" (concept_key: "hero_visual"): Central hero concept dramatically highlighted.
  - "COMPARISON" (concept_key: "comparison"): Side-by-side contrast (before/after, X vs Y).
  - Physics/Space keys: "straight_light_ray", "spacetime_curvature", "light_bending", "einstein_ring", "scale_comparison"
  - Signals keys: "radio_waves", "binary_packets", "frequency_spectrum"

Reply with ONE JSON object only (no markdown):
{{
  "format": "STORY | MYTH-BUST | LIST | HOW-TO | POV | COMPARISON | PERSONAL",
  "angle": "one sentence: the specific take that makes this interesting",
  "hook_options": ["hook 1", "hook 2", "hook 3"],
  "hook": "the chosen hook — scene 1 narration starts with it word for word",
  "hook_text": "2-5 word on-screen headline for the first 3 seconds",
  "title": "punchy title, max 60 chars",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "spoken words for this scene",
      "on_screen_text": "1-4 words",
      "visual_description": "what the viewer sees",
      "search_queries": ["2-4 word query", "broader backup query"],
      "composition": "HERO_VISUAL | PHYSICAL_DEMO | DATA_VIZ | TRANSFORMATION | OBJECT_INTERACTION | MAP_TIMELINE | COMPARISON",
      "concept_key": "hero_visual | physical_demo | data_viz | transformation | object_interaction | straight_light_ray | spacetime_curvature | light_bending",
      "visual_subject": "main subject being visualized",
      "supporting_text": "UPPERCASE LABEL"
    }}
  ],
  "closing": "the final spoken line (also the last words of the last scene)",
  "music_mood": "upbeat | chill | cinematic | inspiring | dramatic | lofi | corporate | emotional",
  "post": {{"caption": "1-2 sentence feed caption that invites comments", "hashtags": ["5-8 tags without #"]}}
}}"""

EDITOR_PROMPT = f"""You are a ruthless short-form video editor who has grown multiple creators past 1M followers. You receive a draft script as JSON. Make it better, then return the FULL improved script in the exact same JSON shape (all fields).

Check and fix:
1. HOOK: would a bored thumb stop in under 2 seconds? If not, rewrite it sharper and more specific. Scene 1 must start with the hook.
2. Every line earns its place. Cut throat-clearing, repetition and generic statements. Replace vague claims with specifics.
3. Sounds human when read aloud: contractions, varied sentence length, natural pauses via punctuation. Remove anything that sounds like AI writing ({", ".join(AI_CLICHES)}).
4. Retention: a re-hook / turn at least every 2-3 scenes; payoff is real; the final line drives comments or loops to the hook.
5. Word limit (given below) is a HARD limit — trim if needed.
6. search_queries & concept_key: ensure valid stock queries and appropriate motion graphics concept_key are present for each scene.
Keep the language/script and format of the draft. Reply with the JSON object only."""


def _language_rule(language: str) -> str:
    return LANGUAGE_RULES.get(
        (language or "english").strip().lower(),
        f"Narration in natural, everyday spoken {language}, written in {language}'s native script "
        "(the way creators actually talk — not formal or textbook language).",
    )


FORMAT_GUIDES = {
    "ugc": (
        "UGC (user-generated content): first person ('I', 'me', 'my'), sounds like a real person talking to their "
        "front camera — honest experience, review, reaction or tip. Casual, a little imperfect ('okay so…', 'honestly'). "
        "Visuals: real people filming themselves, talking to camera, POV hands, everyday rooms, streets, cafés."
    ),
    "storytelling": "STORY: a mini narrative with a setup, a turn and an emotional or surprising payoff. Visuals: people in moments.",
    "explainer": "EXPLAINER: one clear question → simple explanation in 3 beats → 'so next time…' takeaway. Visuals show the thing being explained.",
    "listicle": "LIST: exactly 3-5 numbered, specific items, best one last. Each item gets its own scene.",
    "cinematic": (
        "CINEMATIC: emotional, poetic, slower lines with pauses; awe and beauty. "
        "Visuals: sweeping wide shots, golden hour, slow motion, silhouettes, faces in close-up."
    ),
    "news": (
        "NEWS RECAP: what happened → why it matters → what's next. Neutral, fast, factual; name sources from the research. "
        "Visuals: real places, people reacting, city life, screens."
    ),
    "motivational": "MOTIVATIONAL: second person ('you'), rising intensity, short punchy lines, a challenge at the end. Visuals: people training, working, winning.",
    "pov": "POV / RELATABLE: open with 'POV:' describing a shared everyday moment, then the twist or insight. Visuals: first-person and people in everyday life.",
}


def _build_user_prompt(
    topic: str,
    title: Optional[str],
    duration_seconds: int,
    language: str,
    tone: str,
    audience: str,
    additional_instructions: Optional[str],
    has_user_media: bool = False,
    video_format: str = "auto",
    visual_style: str = "real",
    people_focus: bool = True,
) -> str:
    scene_count = max(4, min(12, round(duration_seconds / 4)))
    lines = [
        f"Topic / idea / trend: {topic}",
        f"Working title: {title}" if title else "",
        f"Length: {duration_seconds} seconds → HARD LIMIT {int(duration_seconds * 2.4)} spoken words total, about {scene_count} scenes",
        f"Language: {_language_rule(language)} search_queries are always in English.",
        f"Tone: {tone}",
        f"Audience: {audience}",
        "Visuals: the creator uploaded their OWN photos/videos for this topic — write it as their personal story; "
        "search_queries are only a backup." if has_user_media else "",
        f"Format chosen by the creator (use it, don't pick another): {FORMAT_GUIDES[video_format]}"
        if video_format in FORMAT_GUIDES else "",
        "Visual style: ANIMATED — search_queries should find illustrations / animated clips (e.g. 'animated rocket launch', 'cartoon city')."
        if visual_style == "animated" else "",
        "People first: at least half of the scenes must show real people — faces, reactions, hands doing things. "
        "Put a person in those search_queries (e.g. 'young woman laughing phone', 'man cooking kitchen')."
        if people_focus and visual_style != "animated" else "",
        f"Extra instructions from the creator (follow them): {additional_instructions}" if additional_instructions else "",
    ]
    return "\n".join(l for l in lines if l)


def _fallback_queries(scene: Dict[str, Any], topic: str) -> List[str]:
    text = scene.get("visual_description") or topic
    words = re.findall(r"[A-Za-z]{3,}", text)
    stop = {"the", "and", "with", "from", "that", "this", "shot", "close", "camera", "showing", "scene", "into", "over"}
    words = [w for w in words if w.lower() not in stop]
    q = " ".join(words[:3]) or topic
    return [q, " ".join(re.findall(r"[A-Za-z]{3,}", topic)[:3]) or q]


_SYMBOLS = re.compile(
    "[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u27BF\u2B00-\u2BFF\uFE0F\u200D#*_~^|<>\\[\\]{}]"
)


def _speakable(text: str) -> str:
    return re.sub(r"\s+", " ", _SYMBOLS.sub(" ", text or "")).strip()


def _count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _make_validator(topic: str, duration_seconds: int):
    max_words = int(duration_seconds * 2.6 * 1.15) + 6

    def validate(obj: Dict[str, Any]) -> Dict[str, Any]:
        scenes = obj.get("scenes")
        if not isinstance(scenes, list) or len(scenes) < 2:
            raise ValueError("'scenes' must be a list with at least 2 scenes")

        clean = []
        for s in scenes:
            if not isinstance(s, dict):
                continue
            narration = _speakable(str(s.get("narration") or ""))
            if not narration:
                continue
            queries = s.get("search_queries")
            if not isinstance(queries, list) or not any(isinstance(q, str) and q.strip() for q in queries):
                queries = _fallback_queries(s, topic)

            composition = str(s.get("composition") or "HERO_VISUAL").strip().upper()
            concept_key = s.get("concept_key") or None
            visual_subject = str(s.get("visual_subject") or s.get("on_screen_text") or "Key Concept").strip()[:40]
            supporting_text = str(s.get("supporting_text") or visual_subject).strip().upper()[:25]

            clean.append({
                "scene_number": len(clean) + 1,
                "duration_seconds": max(2, round(_count_words(narration) / 2.5)),
                "narration": narration,
                "on_screen_text": _speakable(str(s.get("on_screen_text") or ""))[:40],
                "visual_description": str(s.get("visual_description") or "").strip(),
                "search_queries": [q.strip() for q in queries if isinstance(q, str) and q.strip()][:3],
                "camera_notes": str(s.get("camera_notes") or "").strip(),
                # Animation-first fields for Purffle engine
                "composition": composition,
                "concept_key": concept_key,
                "visual_subject": visual_subject,
                "supporting_text": supporting_text,
                "core_claim": narration[:60],
                "visual_action": str(s.get("visual_action") or s.get("visual_description") or "")[:80],
            })
        if len(clean) < 2:
            raise ValueError("fewer than 2 scenes have narration")

        words = sum(_count_words(s["narration"]) for s in clean)
        if words > max_words:
            raise ValueError(
                f"script is {words} spoken words but a {duration_seconds}s video allows at most "
                f"{int(duration_seconds * 2.4)} — shorten the narration, keep the hook"
            )

        hook = _speakable(str(obj.get("hook") or "")) or re.split(r"(?<=[.!?])\s", clean[0]["narration"])[0]
        if not clean[0]["narration"].lower().startswith(hook.lower()[:20]):
            clean[0]["narration"] = f"{hook} {clean[0]['narration']}"

        mood = str(obj.get("music_mood") or "").lower().strip()
        post = obj.get("post") if isinstance(obj.get("post"), dict) else {}
        hashtags = [re.sub(r"[^\w]", "", str(h)) for h in (post.get("hashtags") or [])]

        return {
            "format": str(obj.get("format") or "").strip(),
            "angle": str(obj.get("angle") or "").strip(),
            "hook_options": [str(h) for h in (obj.get("hook_options") or [])][:3],
            "title": str(obj.get("title") or topic)[:120],
            "hook": hook,
            "hook_text": _speakable(str(obj.get("hook_text") or ""))[:60],
            "closing": _speakable(str(obj.get("closing") or "")),
            "scenes": clean,
            "music_mood": mood if mood in MUSIC_MOODS else "cinematic",
            "post": {
                "caption": str(post.get("caption") or obj.get("title") or topic).strip(),
                "hashtags": [h for h in hashtags if h][:8],
            },
            "total_duration_seconds": duration_seconds,
        }
    return validate


def _cliches_in(script: Dict[str, Any]) -> List[str]:
    text = " ".join(s["narration"] for s in script["scenes"]).lower()
    return [c for c in AI_CLICHES if c in text]


async def generate_script(
    topic: str,
    duration_seconds: int = 30,
    language: str = "English",
    tone: str = "energetic",
    audience: str = "general",
    title: Optional[str] = None,
    additional_instructions: Optional[str] = None,
    has_user_media: bool = False,
    polish: bool = True,
    research: Optional[Dict[str, Any]] = None,
    video_format: str = "auto",
    visual_style: str = "real",
    people_focus: bool = True,
) -> Dict[str, Any]:
    """Write (and edit) a short-form, hook-first script with animation metadata. Returns normalised script dict."""
    validate = _make_validator(topic, duration_seconds)
    brief = _build_user_prompt(
        topic, title, duration_seconds, language, tone, audience, additional_instructions, has_user_media,
        video_format, visual_style, people_focus,
    )
    if research:
        brief += "\n\n" + research_brief(research)

    logger.info(f"Writing script: topic={topic!r} duration={duration_seconds}s tone={tone} lang={language}")
    draft = await generate_json(
        [{"role": "system", "content": WRITER_PROMPT}, {"role": "user", "content": brief + "\n\nWrite the script JSON now."}],
        validate=validate, temperature=0.9,
    )
    logger.info(f"Draft: format={draft.get('format')} hook={draft.get('hook')!r} via {draft.get('_llm_provider')}")
    if not polish:
        draft["research"] = research or {}
        return draft

    cliches = _cliches_in(draft)
    notes = [
        f"Hard limit: {int(duration_seconds * 2.4)} spoken words total across all scenes.",
        f"Detected clichés to rewrite: {', '.join(cliches)}" if cliches else "",
    ]
    editor_user = (
        f"Topic: {topic}\nTarget length: {duration_seconds}s\n"
        f"Editor notes: {' '.join(n for n in notes if n)}\n\n"
        f"Draft script JSON to improve:\n{json.dumps(draft, ensure_ascii=False)}"
    )
    try:
        edited = await generate_json(
            [{"role": "system", "content": EDITOR_PROMPT}, {"role": "user", "content": editor_user}],
            validate=validate, temperature=0.7,
        )
        logger.info(f"Edited: hook={edited.get('hook')!r}")
        edited["research"] = research or {}
        return edited
    except LLMError as e:
        logger.warning(f"Editor pass failed, using draft: {e}")
        draft["research"] = research or {}
        return draft


SCENE_REWRITE_PROMPT = """You rewrite ONE scene of a short-form video script so it is sharper, more specific and more human,
while fitting the scenes around it. Keep the same language and roughly the same length. Scene 1 must still open
with a hook. Reply with JSON only:
{"narration": "...", "on_screen_text": "1-4 words", "visual_description": "...", "search_queries": ["2-4 words", "2-3 words"]}"""


async def regenerate_scene(script: Dict[str, Any], index: int, instructions: Optional[str] = None) -> Dict[str, Any]:
    """Rewrite scene `index` (0-based) in the context of the full script."""
    scenes = script.get("scenes") or []
    if not 0 <= index < len(scenes):
        raise ValueError("scene index out of range")
    outline = "\n".join(f"{i + 1}. {s.get('narration', '')}" for i, s in enumerate(scenes))

    def validate(obj: Dict[str, Any]) -> Dict[str, Any]:
        narration = _speakable(str(obj.get("narration") or ""))
        if not narration:
            raise ValueError("empty narration")
        queries = [q.strip() for q in (obj.get("search_queries") or []) if isinstance(q, str) and q.strip()]
        return {
            **scenes[index],
            "narration": narration,
            "on_screen_text": _speakable(str(obj.get("on_screen_text") or ""))[:40],
            "visual_description": str(obj.get("visual_description") or "").strip(),
            "search_queries": queries[:3] or scenes[index].get("search_queries", []),
            "duration_seconds": max(2, round(_count_words(narration) / 2.5)),
        }

    user = (
        f"Video title: {script.get('title', '')}\nLanguage: {script.get('language', 'English')}\n"
        f"Full script:\n{outline}\n\nRewrite scene {index + 1}."
        + (f"\nCreator's instructions: {instructions}" if instructions else "")
    )
    return await generate_json(
        [{"role": "system", "content": SCENE_REWRITE_PROMPT}, {"role": "user", "content": user}],
        validate=validate, temperature=0.85, max_tokens=600,
    )


def script_fields_for_db(script: Dict[str, Any]) -> Dict[str, Any]:
    """The subset of a generated script that is persisted on the script document."""
    return {
        "title": script.get("title"),
        "format": script.get("format", ""),
        "angle": script.get("angle", ""),
        "hook_options": script.get("hook_options", []),
        "hook": script.get("hook", ""),
        "hook_text": script.get("hook_text", ""),
        "closing": script.get("closing", ""),
        "scenes": script.get("scenes", []),
        "music_mood": script.get("music_mood", "cinematic"),
        "post": script.get("post", {}),
        "llm_provider": script.get("_llm_provider"),
        "research": script.get("research") or {},
    }


def script_to_video_prompt(script: Dict[str, Any]) -> str:
    """Flatten a structured script into a single video prompt for fallback video APIs."""
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
