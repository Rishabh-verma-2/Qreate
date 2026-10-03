"""Short-form captions as an ASS subtitle file.

Style: 1-3 word chunks, big bold font, active word highlighted, small pop-in —
the look viewers expect on Reels/Shorts. Plus an on-screen hook headline for
the first ~3 seconds.
"""

import re
from typing import List, Optional

from app.services.media.tts import Word

FONT_NAME = "Poppins ExtraBold"
HIGHLIGHT = "&H0000E5FF&"   # ASS colours are &HBBGGRR — this is #FFE500 yellow
CAPTION_Y = 1290            # lower-middle; clear of the app's bottom UI
HOOK_Y = 300


def _ts(t: float) -> str:
    t = max(t, 0.0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").strip()


def _chunk_words(words: List[Word], max_words: int = 3, max_chars: int = 18) -> List[List[Word]]:
    chunks, cur = [], []
    for w in words:
        cur_len = sum(len(x.text) + 1 for x in cur)
        if cur and (len(cur) >= max_words or cur_len + len(w.text) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w.pause or re.search(r"[.!?,;:]$", w.text):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(
    words: List[Word],
    width: int,
    height: int,
    hook_text: Optional[str] = None,
    hook_end: float = 3.0,
    uppercase: bool = True,
) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT_NAME},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,7,4,5,60,60,0,1
Style: Hook,{FONT_NAME},78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,3,26,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []

    if hook_text:
        text = _clean(hook_text.upper() if uppercase else hook_text)
        lines.append(
            f"Dialogue: 1,{_ts(0.15)},{_ts(hook_end)},Hook,,0,0,0,,"
            f"{{\\pos({width // 2},{HOOK_Y})\\fad(150,250)\\3c&H000000&\\4a&HFF&\\1c&HFFFFFF&\\3a&H40&}}{text}"
        )

    chunks = _chunk_words(words)
    for ci, chunk in enumerate(chunks):
        next_start = chunks[ci + 1][0].start if ci + 1 < len(chunks) else chunk[-1].end + 0.4
        chunk_end = next_start if next_start - chunk[-1].end < 0.5 else chunk[-1].end + 0.25
        tokens = [_clean(w.text.upper() if uppercase else w.text) for w in chunk]
        for wi, w in enumerate(chunk):
            start = w.start
            end = chunk[wi + 1].start if wi + 1 < len(chunk) else chunk_end
            if end <= start:
                continue
            parts = []
            for ti, tok in enumerate(tokens):
                if ti == wi:
                    parts.append(f"{{\\c{HIGHLIGHT}}}{tok}{{\\c&H00FFFFFF&}}")
                else:
                    parts.append(tok)
            pop = "\\fscx88\\fscy88\\t(0,80,\\fscx100\\fscy100)" if wi == 0 else ""
            lines.append(
                f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,"
                f"{{\\pos({width // 2},{CAPTION_Y}){pop}}}{' '.join(parts)}"
            )

    return header + "\n".join(lines) + "\n"
