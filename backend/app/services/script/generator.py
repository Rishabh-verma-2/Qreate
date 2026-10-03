"""Script generation: topic → hook + story + scene plan + post copy.

Two LLM passes, the way a real creator team works:
  1. Writer — picks a proven short-form format and angle, drafts 3 hooks, keeps the
     strongest, and writes the script for the ear.
  2. Editor — scores the draft against retention rules and rewrites weak lines
     (vague claims, AI-sounding phrases, flat rhythm, weak ending). If the edit
     pass fails for any reason the writer's draft is used.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm import LLMError, generate_json

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

WRITER_PROMPT = f"""You are a top short-form creator and head writer for Qoneqt, a community-first social app (Reddit meets Reels). You have studied thousands of viral Reels and YouTube Shorts. You write scripts people watch to the end, rewatch, and comment on.

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

STEP 4 — visuals. Each scene gets 2 stock-footage search queries of 2-4 words: concrete subject + action/setting that a stock site really has ("woman sipping chai balcony", "mumbai local train crowd", "hands typing laptop night"). Prefer people and real moments over objects. If the topic is in India, put "indian" or the city in the query. No text, logos, brands or celebrities. Also give 1-4 words of on_screen_text that capture the scene's key point (a number, a keyword) — used as a bold text card when no footage fits.

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
      "search_queries": ["2-4 word query", "broader 2-3 word backup"]
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
6. search_queries: 2-4 concrete words a stock site actually has, varied shots, people where possible.
Keep the language/script and format of the draft. Reply with the JSON object only."""


def _language_rule(language: str) -> str:
    return LANGUAGE_RULES.get((language or "english").strip().lower(), f"Narration in natural spoken {language}.")


def _build_user_prompt(
    topic: str,
    title: Optional[str],
    duration_seconds: int,
    language: str,
    tone: str,
    audience: str,
    additional_instructions: Optional[str],
    has_user_media: bool = False,
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


# Emoji, pictographs, arrows and other symbols the voice would read out loud
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
            clean.append({
                "scene_number": len(clean) + 1,
                "duration_seconds": max(2, round(_count_words(narration) / 2.5)),
                "narration": narration,
                "on_screen_text": _speakable(str(s.get("on_screen_text") or ""))[:40],
                "visual_description": str(s.get("visual_description") or "").strip(),
                "search_queries": [q.strip() for q in queries if isinstance(q, str) and q.strip()][:3],
                "camera_notes": str(s.get("camera_notes") or "").strip(),
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
) -> Dict[str, Any]:
    """Write (and edit) a short-form, hook-first script. Returns the normalised script dict."""
    validate = _make_validator(topic, duration_seconds)
    brief = _build_user_prompt(
        topic, title, duration_seconds, language, tone, audience, additional_instructions, has_user_media,
    )

    logger.info(f"Writing script: topic={topic!r} duration={duration_seconds}s tone={tone} lang={language}")
    draft = await generate_json(
        [{"role": "system", "content": WRITER_PROMPT}, {"role": "user", "content": brief + "\n\nWrite the script JSON now."}],
        validate=validate, temperature=0.9,
    )
    logger.info(f"Draft: format={draft.get('format')} hook={draft.get('hook')!r} via {draft.get('_llm_provider')}")
    if not polish:
        return draft

    draft_json = json.dumps({k: v for k, v in draft.items() if not k.startswith("_") and k != "total_duration_seconds"}, ensure_ascii=False)
    cliches = _cliches_in(draft)
    try:
        edited = await generate_json(
            [
                {"role": "system", "content": EDITOR_PROMPT},
                {"role": "user", "content": (
                    f"{brief}\n"
                    + (f"Draft contains AI-sounding phrases you must remove: {', '.join(cliches)}\n" if cliches else "")
                    + f"\nDRAFT:\n{draft_json}\n\nReturn the improved script JSON."
                )},
            ],
            validate=validate, temperature=0.6,
        )
        logger.info(f"Edited: hook={edited.get('hook')!r}")
        return edited
    except LLMError as e:
        logger.warning(f"Editor pass failed, using draft: {e}")
        return draft


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
    }
