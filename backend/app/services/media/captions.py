"""Short-form captions as an ASS subtitle file.

Style: 1-3 word chunks, big bold font, active word highlighted, small pop-in —
the look viewers expect on Reels/Shorts. Plus an on-screen hook headline for
the first ~3 seconds.
"""

import re
from typing import List, Optional

from app.services.media.tts import Word

FONT_NAME = "Poppins ExtraBold"
# Scripts Poppins doesn't cover get their own bundled Noto font (Poppins covers Latin + Devanagari)
SCRIPT_FONTS = {
    "Tamil": "Noto Sans Tamil", "Telugu": "Noto Sans Telugu", "Bengali": "Noto Sans Bengali",
    "Gujarati": "Noto Sans Gujarati", "Kannada": "Noto Sans Kannada", "Malayalam": "Noto Sans Malayalam",
    "Urdu": "Noto Sans Arabic", "Arabic": "Noto Sans Arabic",
}
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


CAPTION_STYLES = {
    # name: (font size, uppercase allowed, border style, outline, shadow, max words per chunk, pop-in)
    "bold": (92, True, 1, 7, 4, 3, True),     # creator "pop" captions
    "clean": (70, False, 1, 3, 2, 4, False),  # understated, sentence case (UGC / vlog look)
    "boxed": (76, True, 3, 14, 0, 3, True),   # text on a solid box (news / explainer look)
}


def build_ass(
    words: List[Word],
    width: int,
    height: int,
    hook_text: Optional[str] = None,
    hook_end: float = 3.0,
    uppercase: bool = True,
    theme=None,
    caption_style: str = "bold",
    language: str = "English",
) -> str:
    from app.services.media.themes import ass_color, get_theme

    theme = theme or get_theme(None)
    size, allow_upper, border, outline, shadow, max_words, pop_in = CAPTION_STYLES.get(caption_style, CAPTION_STYLES["bold"])
    latin = uppercase  # caller passes uppercase=True only for Latin-script languages
    uppercase = uppercase and allow_upper
    bold_flag, spacing, font = 0, 1, FONT_NAME
    if not latin:
        # Letter spacing disables complex-script shaping in libass (Tamil/Hindi glyphs fall apart),
        # so non-Latin captions use spacing 0, the script's own font, a bigger size and bold.
        font = SCRIPT_FONTS.get(language, FONT_NAME)
        size, bold_flag, spacing = int(size * 1.1), -1, 0
        if border == 1:
            outline = max(outline, 5)
    text_c, hi_c = ass_color(theme.text), ass_color(theme.highlight)
    back = "&H64000000" if border == 3 else "&H90000000"
    # On a boxed style the box is drawn with the outline colour
    outline_c = "&H59000000" if border == 3 else "&H00000000"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{text_c},{text_c},{outline_c},{back},{bold_flag},0,0,0,100,100,{spacing},0,{border},{outline},{shadow},5,60,60,0,1
Style: Hook,{font},78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,3,26,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []

    if hook_text:
        text = _clean(hook_text.upper() if uppercase else hook_text)
        # Hook banner uses the theme accent as its box colour, text in black or white for contrast
        r, g, b = theme.highlight
        dark_text = (0.299 * r + 0.587 * g + 0.114 * b) > 160
        lines.append(
            f"Dialogue: 1,{_ts(0.15)},{_ts(hook_end)},Hook,,0,0,0,,"
            f"{{\\pos({width // 2},{HOOK_Y})\\fad(150,250)\\3c{hi_c}\\1c{'&H000000&' if dark_text else '&HFFFFFF&'}}}{text}"
        )

    chunks = _chunk_words(words, max_words=max_words, max_chars=18 if max_words <= 3 else 24)
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
                    parts.append(f"{{\\c{hi_c}}}{tok}{{\\c{text_c}}}")
                else:
                    parts.append(tok)
            pop = "\\fscx88\\fscy88\\t(0,80,\\fscx100\\fscy100)" if (wi == 0 and pop_in) else ""
            lines.append(
                f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,"
                f"{{\\pos({width // 2},{CAPTION_Y}){pop}}}{' '.join(parts)}"
            )

    return header + "\n".join(lines) + "\n"
