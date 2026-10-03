"""Neural voiceover with word-level timestamps (Microsoft Edge TTS — free, no key).

The whole script is spoken in ONE pass so intonation flows across sentences like a
real person talking (per-scene clips reset the prosody every few seconds, which is
the most obvious "AI voice" tell). Scene cut points are then derived from the word
timestamps, so visuals change exactly when the next line starts.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import edge_tts

from app.services.media.ffmpeg import probe_duration

logger = logging.getLogger(__name__)

# (language, gender) → voice. The "Multilingual" en-US voices are the most natural Edge voices.
VOICES: Dict[Tuple[str, str], str] = {
    ("english", "male"): "en-US-AndrewMultilingualNeural",
    ("english", "female"): "en-US-AvaMultilingualNeural",
    ("hinglish", "male"): "en-IN-PrabhatNeural",
    ("hinglish", "female"): "en-IN-NeerjaExpressiveNeural",
    ("hindi", "male"): "hi-IN-MadhurNeural",
    ("hindi", "female"): "hi-IN-SwaraNeural",
    ("spanish", "male"): "es-ES-AlvaroNeural",
    ("spanish", "female"): "es-ES-ElviraNeural",
    ("french", "male"): "fr-FR-RemyMultilingualNeural",
    ("french", "female"): "fr-FR-VivienneMultilingualNeural",
    ("german", "male"): "de-DE-FlorianMultilingualNeural",
    ("german", "female"): "de-DE-SeraphinaMultilingualNeural",
    ("portuguese", "male"): "pt-BR-AntonioNeural",
    ("portuguese", "female"): "pt-BR-FranciscaNeural",
}
# Energetic English reads better with Brian's casual delivery
ENERGETIC_MALE_EN = "en-US-BrianMultilingualNeural"
DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"

# Delivery per tone: (rate, pitch). Short-form voiceovers run slightly fast.
TONE_DELIVERY = {
    "energetic": ("+10%", "+0Hz"),
    "entertaining": ("+10%", "+0Hz"),
    "conversational": ("+6%", "+0Hz"),
    "educational": ("+5%", "+0Hz"),
    "professional": ("+4%", "-1Hz"),
    "inspirational": ("+0%", "-1Hz"),
    "dramatic": ("-3%", "-2Hz"),
    "calm": ("-4%", "-1Hz"),
}


@dataclass
class Word:
    start: float
    end: float
    text: str
    pause: bool = False  # punctuation follows this word in the script (natural caption break)


@dataclass
class Narration:
    audio_path: str
    duration: float
    words: List[Word]
    scene_starts: List[float] = field(default_factory=list)  # seconds where each script line begins


def pick_voice(language: str, tone: str, gender: str = "male") -> str:
    lang = (language or "english").strip().lower()
    gender = "female" if (gender or "").lower().startswith("f") else "male"
    if lang == "english" and gender == "male" and (tone or "").lower() in ("energetic", "entertaining"):
        return ENERGETIC_MALE_EN
    return VOICES.get((lang, gender)) or VOICES.get((lang, "male")) or DEFAULT_VOICE


def delivery_for(tone: str) -> Tuple[str, str]:
    return TONE_DELIVERY.get((tone or "").lower(), ("+6%", "+0Hz"))


def _locate_words(words: List[Word], text: str) -> List[int]:
    """Character offset of each spoken word in `text` (-1 if not found); also marks pauses."""
    positions, pos, lower = [], 0, text.lower()
    for w in words:
        idx = lower.find(w.text.lower(), pos)
        if idx < 0:
            positions.append(-1)
            continue
        pos = idx + len(w.text)
        w.pause = bool(re.match(r"\s*[.,!?;:—–…।]|\s+-\s", text[pos:pos + 3]))
        positions.append(idx)
    return positions


def _estimate_words(text: str, duration: float) -> List[Word]:
    """Fallback timing when the voice emits no word boundaries: spread by word length."""
    tokens = text.split()
    if not tokens:
        return []
    weights = [max(len(re.sub(r"\W", "", t)), 2) for t in tokens]
    total = sum(weights)
    t, out = 0.05, []
    span = max(duration - 0.1, 0.5)
    for tok, w in zip(tokens, weights):
        d = span * w / total
        out.append(Word(t, t + d, tok))
        t += d
    return out


async def synthesize(text: str, audio_path: str, voice: str, rate: str = "+6%", pitch: str = "+0Hz") -> Narration:
    """Speak `text` into `audio_path` (mp3). Retries transient Edge-TTS failures."""
    text = re.sub(r"\s+", " ", text).strip() or "..."
    last_err = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
            words: List[Word] = []
            with open(audio_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start = chunk["offset"] / 1e7
                        words.append(Word(start, start + chunk["duration"] / 1e7, chunk["text"]))
            duration = await probe_duration(audio_path)
            if duration <= 0:
                raise RuntimeError("empty audio")
            if not words:
                words = _estimate_words(text, duration)
            _locate_words(words, text)
            return Narration(audio_path, duration, words)
        except Exception as e:  # edge-tts raises a variety of transport errors
            last_err = e
            logger.warning(f"Edge-TTS attempt {attempt + 1} failed ({voice}): {e}")
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Voice synthesis failed: {last_err}")


async def synthesize_script(lines: List[str], audio_path: str, voice: str, tone: str = "") -> Narration:
    """Speak all script lines in one continuous take and return per-line start times."""
    clean = []
    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if line and not re.search(r"[.!?…।]$", line):
            line += "."
        clean.append(line or "…")

    # Character span of each line inside the joined text
    spans, cursor = [], 0
    for line in clean:
        spans.append((cursor, cursor + len(line)))
        cursor += len(line) + 1
    full_text = " ".join(clean)

    rate, pitch = delivery_for(tone)
    narration = await synthesize(full_text, audio_path, voice, rate=rate, pitch=pitch)
    positions = _locate_words(narration.words, full_text)

    starts: List[float] = []
    for li, (a, b) in enumerate(spans):
        first = next((w for w, p in zip(narration.words, positions) if a <= p < b), None)
        if first is not None:
            # Cut a beat before the line is spoken, like an editor cutting on the breath
            starts.append(0.0 if li == 0 else max(first.start - 0.12, 0.0))
        else:
            starts.append(-1.0)

    # Fill any line we couldn't locate proportionally by character length
    total_chars = max(len(full_text), 1)
    for i, s in enumerate(starts):
        if s < 0:
            starts[i] = narration.duration * spans[i][0] / total_chars
    for i in range(1, len(starts)):  # enforce monotonic, min 0.8s per scene
        starts[i] = max(starts[i], starts[i - 1] + 0.8)

    narration.scene_starts = starts
    return narration
