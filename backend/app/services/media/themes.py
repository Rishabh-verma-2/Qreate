"""Color themes: caption highlight, hook banner, text-card palette and video grade.

`accent_color` (a #RRGGBB the creator picks) overrides the theme's highlight.
"""

import re
from dataclasses import dataclass, replace
from typing import Optional, Tuple

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    highlight: RGB          # active caption word, card accent bar
    text: RGB               # caption base color
    card_top: RGB           # text-card gradient
    card_bottom: RGB
    grade: str              # FFmpeg filter chain applied to every shot


THEMES = {
    "vibrant": Theme("vibrant", "Vibrant pop", (255, 229, 0), (255, 255, 255), (24, 32, 58), (88, 60, 140),
                     "eq=contrast=1.05:saturation=1.12:brightness=0.01"),
    "warm": Theme("warm", "Warm sunset", (255, 159, 28), (255, 248, 240), (60, 24, 16), (170, 80, 40),
                  "eq=contrast=1.04:saturation=1.08,colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.03:bm=-0.03"),
    "cool": Theme("cool", "Cool tech", (61, 217, 255), (240, 250, 255), (8, 24, 48), (20, 90, 130),
                  "eq=contrast=1.05:saturation=1.04,colorbalance=rs=-0.03:bs=0.05:bm=0.03"),
    "neon": Theme("neon", "Neon night", (255, 60, 172), (255, 255, 255), (20, 6, 40), (90, 20, 120),
                  "eq=contrast=1.08:saturation=1.25:brightness=-0.01"),
    "luxury": Theme("luxury", "Luxury gold", (212, 175, 55), (250, 246, 236), (18, 16, 14), (60, 48, 30),
                    "eq=contrast=1.07:saturation=0.92,colorbalance=rs=0.03:bs=-0.03"),
    "minimal": Theme("minimal", "Clean minimal", (255, 255, 255), (255, 255, 255), (30, 30, 34), (70, 70, 78),
                     "eq=contrast=1.02:saturation=1.0"),
    "mono": Theme("mono", "Black & white", (255, 255, 255), (230, 230, 230), (10, 10, 10), (60, 60, 60),
                  "hue=s=0,eq=contrast=1.12:brightness=0.01"),
}

DEFAULT_THEME = "vibrant"


def _hex(color: str) -> Optional[RGB]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", (color or "").strip())
    if not m:
        return None
    v = m.group(1)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def get_theme(name: Optional[str], accent_color: Optional[str] = None) -> Theme:
    theme = THEMES.get((name or "").lower(), THEMES[DEFAULT_THEME])
    custom = _hex(accent_color or "")
    return replace(theme, highlight=custom) if custom else theme


def ass_color(rgb: RGB, alpha: int = 0) -> str:
    """ASS colours are &HAABBGGRR."""
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"
