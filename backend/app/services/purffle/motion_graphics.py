"""Procedural motion graphics generator for PurffleShorts V3 — Scene Composition Engine.

Renders lightweight, high-fidelity 1080x1920 (9:16) educational animated diagrams,
process visualizations, and physics motion sequences using Pillow and FFmpeg.
Runs 100% locally with zero external API dependencies.

V3 Composition System
---------------------
Every scene is composed through a SceneComposer that:
  - Measures bounding boxes for every element before placement
  - Prevents element collisions via a collision registry
  - Selects from 7 composition types (A-G) based on scene metadata
  - Ensures cinematic gradient background for all frames
  - Maintains transition continuity between scenes
"""

import logging
import math
import os
import random
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM: 9:16 LAYOUT GRID & DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────

WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Layout Grid Tokens
GRID_MARGIN_X = 72                          # Safe margin left/right (936px content width)
GRID_WIDTH = WIDTH - 2 * GRID_MARGIN_X      # 936px content width
CX = WIDTH // 2                             # 540px horizontal center

# Vertical Layout Zones (Strict 9:16 boundaries)
HUD_TOP_Y = 96                              # Top safe area padding
HUD_MAX_HEIGHT = 160

VISUAL_ZONE_TOP = 280
VISUAL_ZONE_BOTTOM = 1580
VISUAL_ZONE_CENTER_Y = (VISUAL_ZONE_TOP + VISUAL_ZONE_BOTTOM) // 2  # 930px

CAPTION_DEFAULT_BOTTOM = 1820               # 100px bottom safe zone for mobile gesture bars
CAPTION_TOP_FALLBACK = 280                  # Safe zone if bottom is occupied

# Spacing Tokens (multiples of 8)
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 24
SPACE_LG = 32
SPACE_XL = 48

# Corner Radii
RADIUS_SM = 10
RADIUS_MD = 16
RADIUS_LG = 24

# Typography Colors
COLOR_WHITE = (255, 255, 255)
COLOR_TEXT_PRIMARY = (248, 250, 252)
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_TEXT_DIM = (100, 116, 139)

# Accent Colors
CYAN_ACCENT = (0, 225, 255)
CYAN_GLOW = (0, 160, 230)
GOLD_ACCENT = (255, 185, 30)
GOLD_GLOW = (255, 120, 10)
EMERALD_ACCENT = (16, 185, 129)
VIOLET_ACCENT = (168, 85, 247)

# Surface Colors
BG_TOP = (10, 16, 28)
BG_BOTTOM = (4, 7, 13)
GRID_COLOR = (20, 32, 54)
BADGE_BG = (10, 16, 28)
BADGE_BORDER = (32, 50, 80)
WHITE = COLOR_WHITE
MUTED_TEXT = COLOR_TEXT_MUTED


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load high-quality font from macOS, Linux, or Windows system fonts, or fallback to default."""
    font_candidates = [
        # macOS Fonts
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFPro.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        # Windows Fonts
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        # Linux Fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for cand in font_candidates:
        if os.path.isfile(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _ease_in_out(t: float) -> float:
    """Smoothstep easing function for organic animation momentum."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ease_out_cubic(t: float) -> float:
    """Ease-out cubic for snappier element entrances."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


# ─────────────────────────────────────────────────────────────────────────────
# SCENE COMPOSITION SYSTEM — BoundingBox + SceneComposer
# ─────────────────────────────────────────────────────────────────────────────

class CompositionType(Enum):
    """12 visual composition archetypes (A-L) for educational Shorts."""
    HERO_VISUAL        = "A"   # Large visual dominates, minimal text
    PHYSICAL_DEMO      = "B"   # Objects move & interact, force vectors, physical demonstration
    PROCESS_FLOW       = "C"   # Genuine multi-step sequential process
    TRANSFORMATION     = "D"   # Before → after morphing or state transformation
    COMPARISON         = "E"   # Dual-panel or side-by-side comparison
    CLOSE_UP           = "F"   # Macro / component focus
    FULL_DIAGRAM       = "G"   # Full-screen annotated diagram
    CINEMATIC          = "H"   # Cinematic visual with subtle overlay
    DATA_VIZ           = "I"   # Growth curve, metric acceleration, data visualization
    MAP_TIMELINE       = "J"   # Chronological or spatial timeline / trajectory
    OBJECT_INTERACTION = "K"   # Two or more objects interacting / colliding / exchanging
    COMBINED_SYSTEM    = "L"   # Multi-element coordinated system

    # Backwards compatibility aliases
    ZOOM_IN            = "F"
    CINEMATIC_CAPTION  = "H"


@dataclass
class BoundingBox:
    """Axis-aligned bounding box with metadata for collision detection."""
    x0: int
    y0: int
    x1: int
    y1: int
    label: str = ""
    priority: int = 0   # Higher priority elements (10=primary visual) never get covered by text (6=caption)

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def cx(self) -> int:
        return (self.x0 + self.x1) // 2

    @property
    def cy(self) -> int:
        return (self.y0 + self.y1) // 2

    def intersects(self, other: "BoundingBox", margin: int = 8) -> bool:
        """True if this box overlaps `other` (with optional safety margin)."""
        return not (
            self.x1 + margin <= other.x0
            or other.x1 + margin <= self.x0
            or self.y1 + margin <= other.y0
            or other.y1 + margin <= self.y0
        )

    def pad(self, px: int) -> "BoundingBox":
        return BoundingBox(self.x0 - px, self.y0 - px, self.x1 + px, self.y1 + px, self.label, self.priority)


class SceneComposer:
    """
    Layout manager for a single scene frame with active 9:16 grid alignment and collision avoidance.
    """

    SAFE_MARGIN = SPACE_MD     # 24px gap enforced between all registered elements
    EDGE_PAD    = GRID_MARGIN_X # 72px strict margin from canvas left/right

    def __init__(self, composition: CompositionType = CompositionType.HERO_VISUAL):
        self.composition = composition
        self._registry: List[BoundingBox] = []

    # ── Zone reservation ──────────────────────────────────────────────────────

    def reserve_hud(self, height: int = HUD_MAX_HEIGHT, y_start: int = HUD_TOP_Y) -> BoundingBox:
        """Reserve the top information-hierarchy badge zone."""
        bb = BoundingBox(
            x0=self.EDGE_PAD,
            y0=y_start,
            x1=WIDTH - self.EDGE_PAD,
            y1=y_start + height,
            label="hud",
            priority=8,
        )
        self._register(bb)
        return bb

    def reserve_caption(self, height: int = 180) -> BoundingBox:
        """Reserve the bottom caption/narration zone."""
        y0 = CAPTION_DEFAULT_BOTTOM - height
        bb = BoundingBox(
            x0=self.EDGE_PAD,
            y0=y0,
            x1=WIDTH - self.EDGE_PAD,
            y1=CAPTION_DEFAULT_BOTTOM,
            label="caption",
            priority=6,
        )
        self._register(bb)
        return bb

    def reserve_visual(self, preferred_y0: Optional[int] = None, preferred_height: Optional[int] = None) -> BoundingBox:
        """
        Reserve the primary visual zone. Priority 10: The visual carries the explanation.
        Auto-fits between hud and caption.
        """
        hud_bb     = self._find("hud")
        caption_bb = self._find("caption")

        top    = (hud_bb.y1 + self.SAFE_MARGIN)     if hud_bb     else VISUAL_ZONE_TOP
        bottom = (caption_bb.y0 - self.SAFE_MARGIN)  if caption_bb else (CAPTION_DEFAULT_BOTTOM - 200)

        if preferred_y0 is not None:
            top = max(top, preferred_y0)
        if preferred_height is not None:
            bottom = min(bottom, top + preferred_height)

        bb = BoundingBox(
            x0=self.EDGE_PAD,
            y0=top,
            x1=WIDTH - self.EDGE_PAD,
            y1=bottom,
            label="visual",
            priority=10,
        )
        self._register(bb)
        return bb

    def reserve_panel(self, label: str, x0: int, y0: int, x1: int, y1: int, priority: int = 5) -> BoundingBox:
        """Reserve an arbitrary named zone."""
        bb = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1, label=label, priority=priority)
        self._register(bb)
        return bb

    # ── Measurement helpers ───────────────────────────────────────────────────

    @staticmethod
    def measure_text(text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        """Return (width, height) of rendered text string using exact bounding box metrics."""
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            w, h = font.getsize(text)  # type: ignore[attr-defined]
            return w, h

    @staticmethod
    def measure_multiline(text: str, font: ImageFont.ImageFont, max_width: int) -> Tuple[int, int, List[str]]:
        """
        Word-wrap `text` to `max_width` pixels and return
        (total_width, total_height, wrapped_lines).
        """
        words = text.split()
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            w, _ = SceneComposer.measure_text(candidate, font)
            if w <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        if not lines:
            return 0, 0, []

        line_h = SceneComposer.measure_text("Ag", font)[1]
        total_h = int(line_h * 1.35 * len(lines))
        max_w = max(SceneComposer.measure_text(l, font)[0] for l in lines)
        return max_w, total_h, lines

    # ── Collision resolution & Interval-Aware Placement ──────────────────────

    def compute_safe_caption_placement(
        self,
        box_h: int,
        animated_visual_bounds: Optional[List[BoundingBox]] = None,
    ) -> Tuple[int, int]:
        """
        Calculates safe (y0, y1) for caption across entire animation interval.
        Text priority: Primary Visual (10) > Supporting Visual (8) > Subtitles (6).
        The primary visual must NEVER be obscured by text.
        """
        hud_bb = self._find("hud")
        top_safe_y = (hud_bb.y1 + self.SAFE_MARGIN) if hud_bb else (HUD_TOP_Y + HUD_MAX_HEIGHT + SPACE_MD)
        bottom_y0 = CAPTION_DEFAULT_BOTTOM - box_h

        cand_bottom = BoundingBox(self.EDGE_PAD, bottom_y0, WIDTH - self.EDGE_PAD, bottom_y0 + box_h, "caption", 6)

        # Check collision against registered static boxes (priority 10 visual)
        collides_bottom = any(
            cand_bottom.intersects(r, self.SAFE_MARGIN)
            for r in self._registry if r.label != "caption" and r.priority > cand_bottom.priority
        )

        # Check collision against animated visual trajectory across the entire interval
        if not collides_bottom and animated_visual_bounds:
            collides_bottom = any(
                cand_bottom.intersects(avb, self.SAFE_MARGIN)
                for avb in animated_visual_bounds
            )

        if not collides_bottom:
            self._register(cand_bottom)
            return bottom_y0, bottom_y0 + box_h

        # Collision at bottom! Candidate: Top safe zone directly beneath HUD badge
        cand_top = BoundingBox(self.EDGE_PAD, top_safe_y, WIDTH - self.EDGE_PAD, top_safe_y + box_h, "caption", 6)
        collides_top = any(
            cand_top.intersects(r, self.SAFE_MARGIN)
            for r in self._registry if r.label != "caption" and r.priority > cand_top.priority
        )
        if animated_visual_bounds:
            collides_top = collides_top or any(
                cand_top.intersects(avb, self.SAFE_MARGIN)
                for avb in animated_visual_bounds
            )

        if not collides_top:
            self._register(cand_top)
            return top_safe_y, top_safe_y + box_h

        # Fallback: find first safe vertical band
        safe_y = self.find_safe_y(WIDTH - 2 * self.EDGE_PAD, box_h, top_safe_y)
        final_box = BoundingBox(self.EDGE_PAD, safe_y, WIDTH - self.EDGE_PAD, safe_y + box_h, "caption", 6)
        self._register(final_box)
        return safe_y, safe_y + box_h

    def find_safe_y(self, width: int, height: int, preferred_y: int) -> int:
        """Scan downward until no collision with higher priority registered boxes."""
        x0 = (WIDTH - width) // 2
        x1 = x0 + width
        y = preferred_y
        max_attempts = 40
        for _ in range(max_attempts):
            candidate = BoundingBox(x0, y, x1, y + height)
            if not any(candidate.intersects(r, self.SAFE_MARGIN) for r in self._registry if r.priority >= 8):
                return y
            y += self.SAFE_MARGIN + 4
        return preferred_y

    def is_clear(self, bb: BoundingBox) -> bool:
        """True if `bb` does not collide with any registered element."""
        return not any(bb.intersects(r, self.SAFE_MARGIN) for r in self._registry)

    def validate(self) -> List[str]:
        """Validate layout against 9:16 safe bounds, element collisions, and margin integrity."""
        errors: List[str] = []
        for i, bb in enumerate(self._registry):
            if bb.x0 < 0 or bb.y0 < 0 or bb.x1 > WIDTH or bb.y1 > HEIGHT:
                errors.append(f"Element '{bb.label}' [{bb.x0},{bb.y0},{bb.x1},{bb.y1}] exceeds canvas bounds {WIDTH}x{HEIGHT}")
            if bb.x0 >= bb.x1 or bb.y0 >= bb.y1:
                errors.append(f"Element '{bb.label}' has invalid negative/zero dimension [{bb.x0},{bb.y0},{bb.x1},{bb.y1}]")
            for j in range(i + 1, len(self._registry)):
                other = self._registry[j]
                if bb.priority != other.priority and bb.intersects(other, margin=0):
                    errors.append(f"Visual collision: '{bb.label}' (priority {bb.priority}) intersects '{other.label}' (priority {other.priority})")
        return errors

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _register(self, bb: BoundingBox) -> None:
        self._registry.append(bb)

    def _find(self, label: str) -> Optional[BoundingBox]:
        for bb in self._registry:
            if bb.label == label:
                return bb
        return None


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL CONTEXTUAL BACKGROUND SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_background_family(
    metadata: Optional[Dict[str, Any]] = None,
    title: str = "",
    narration: str = "",
) -> str:
    """Intelligently determine contextual background family from scene metadata or semantic context."""
    meta = metadata or {}
    explicit = str(meta.get("background_family") or "").strip().lower()
    valid_families = {
        "clean_studio", "optical_lens", "microscopic_sensor", "technical_engineering",
        "atmospheric_cinematic", "natural_organic", "data_computational", "deep_space", "editorial_minimal"
    }
    if explicit in valid_families:
        return explicit

    subject = str(meta.get("visual_subject") or "").lower()
    action = str(meta.get("visual_action") or "").lower()
    claim = str(meta.get("core_claim") or "").lower()
    combined = f"{title} {narration} {subject} {action} {claim}".lower()

    if any(w in combined for w in ["camera", "lens", "photo", "optic", "aperture", "refract", "focus", "focal"]):
        return "optical_lens"
    if any(w in combined for w in ["sensor", "pixel", "silicon", "bayer", "photodiode", "semiconductor", "chip", "electron charge"]):
        return "microscopic_sensor"
    if any(w in combined for w in ["space", "star", "black hole", "cosm", "galaxy", "relativity", "spacetime", "astronom"]):
        return "deep_space"
    if any(w in combined for w in ["engine", "plane", "thrust", "aerospace", "hardware", "drag", "lift", "gravity", "force vector"]):
        return "technical_engineering"
    if any(w in combined for w in ["algorithm", "software", "code", "isp", "processing", "comput", "digital", "network", "packet", "signal", "radio wave"]):
        return "data_computational"
    if any(w in combined for w in ["cook", "melt", "butter", "heat", "temperature", "food", "bio", "plant", "nature", "organic", "cell"]):
        return "natural_organic"
    if any(w in combined for w in ["interest", "finance", "money", "history", "timeline", "economy", "document"]):
        return "editorial_minimal"

    return "clean_studio"


def _draw_contextual_bg(img: Image.Image, bg_family: str = "clean_studio", seed: int = 0) -> None:
    """Render a context-aware professional background based on semantic environment family."""
    draw = ImageDraw.Draw(img)
    rng = random.Random(seed % 30)

    # 1. Base Gradient definitions per family
    if bg_family == "optical_lens":
        top_col = (10, 16, 28)
        bot_col = (4, 7, 13)
    elif bg_family == "microscopic_sensor":
        top_col = (12, 18, 30)
        bot_col = (6, 9, 16)
    elif bg_family == "technical_engineering":
        top_col = (10, 16, 26)
        bot_col = (6, 10, 18)
    elif bg_family == "atmospheric_cinematic":
        top_col = (16, 22, 34)
        bot_col = (8, 11, 18)
    elif bg_family == "natural_organic":
        top_col = (22, 18, 14)
        bot_col = (10, 14, 12)
    elif bg_family == "data_computational":
        top_col = (8, 14, 26)
        bot_col = (4, 8, 16)
    elif bg_family == "deep_space":
        top_col = (6, 9, 20)
        bot_col = (12, 18, 38)
    elif bg_family == "editorial_minimal":
        top_col = (14, 18, 26)
        bot_col = (7, 10, 15)
    else:  # clean_studio
        top_col = (14, 20, 32)
        bot_col = (8, 12, 20)

    # Vertical smooth vignette gradient
    for y in range(HEIGHT):
        t = y / float(HEIGHT)
        r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
        g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
        b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Family-specific environmental details (subtle, non-competing)
    cx, cy = CX, VISUAL_ZONE_CENTER_Y

    if bg_family == "optical_lens":
        for r_lens in [260, 420, 600, 780]:
            draw.ellipse([cx - r_lens, cy - r_lens, cx + r_lens, cy + r_lens],
                         outline=(16, 26, 44), width=1)
        streak_y = cy - 20
        draw.line([(80, streak_y), (WIDTH - 80, streak_y)], fill=(15, 28, 48), width=2)
        draw.ellipse([cx - 180, cy - 30, cx + 180, cy + 30], outline=(20, 35, 60), width=1)

    elif bg_family == "microscopic_sensor":
        for gx in range(GRID_MARGIN_X, WIDTH - GRID_MARGIN_X, 48):
            draw.line([(gx, 280), (gx, 1600)], fill=(15, 22, 36), width=1)
        for gy in range(300, 1580, 48):
            draw.line([(GRID_MARGIN_X, gy), (WIDTH - GRID_MARGIN_X, gy)], fill=(15, 22, 36), width=1)
        pad_size = 18
        for px, py in [(GRID_MARGIN_X + 10, 300), (WIDTH - GRID_MARGIN_X - 10, 300),
                       (GRID_MARGIN_X + 10, 1560), (WIDTH - GRID_MARGIN_X - 10, 1560)]:
            draw.rectangle([px - pad_size // 2, py - pad_size // 2, px + pad_size // 2, py + pad_size // 2],
                           fill=(20, 30, 48), outline=(32, 48, 72), width=1)

    elif bg_family == "technical_engineering":
        for gx in range(GRID_MARGIN_X, WIDTH - GRID_MARGIN_X, 64):
            draw.line([(gx, 280), (gx, 1600)], fill=(16, 24, 40), width=1)
        for gy in range(320, 1560, 64):
            draw.line([(GRID_MARGIN_X, gy), (WIDTH - GRID_MARGIN_X, gy)], fill=(16, 24, 40), width=1)
        for qx, qy in [(CX, 600), (CX, 1200)]:
            draw.line([(qx - 14, qy), (qx + 14, qy)], fill=(30, 45, 75), width=2)
            draw.line([(qx, qy - 14), (qx, qy + 14)], fill=(30, 45, 75), width=2)

    elif bg_family == "data_computational":
        for gx in range(GRID_MARGIN_X + 24, WIDTH - GRID_MARGIN_X, 56):
            draw.line([(gx, 280), (gx, 1600)], fill=(14, 22, 38), width=1)
        for _ in range(25):
            nx = GRID_MARGIN_X + 24 + rng.randint(0, 14) * 56
            ny = 320 + rng.randint(0, 20) * 60
            draw.ellipse([nx - 3, ny - 3, nx + 3, ny + 3], fill=(22, 38, 64))

    elif bg_family == "deep_space":
        for _ in range(80):
            sx = rng.randint(40, WIDTH - 40)
            sy = rng.randint(80, HEIGHT - 80)
            brightness = rng.randint(90, 220)
            r = 1 if brightness < 180 else 2
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(brightness, brightness, int(brightness * 1.15)))

    elif bg_family == "clean_studio":
        for r_spot in range(480, 80, -40):
            alpha = int(12 * (1.0 - r_spot / 480.0))
            draw.ellipse([cx - r_spot, cy - r_spot, cx + r_spot, cy + r_spot],
                         outline=(16 + alpha, 22 + alpha, 36 + alpha * 2), width=2)


def _draw_gradient_bg(img: Image.Image, seed: int = 0) -> None:
    """Backwards-compatibility wrapper for contextual background."""
    _draw_contextual_bg(img, bg_family="clean_studio", seed=seed)


def _draw_subject_backdrop(draw: ImageDraw.ImageDraw, bb: BoundingBox, color=(8, 12, 22)) -> None:
    """Draw a soft darkened ambient backdrop behind active visual elements to maximize foreground contrast."""
    pad = 20
    draw.rounded_rectangle(
        [bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad],
        radius=20,
        fill=color,
        outline=(20, 32, 52),
        width=1,
    )


def _draw_hud_badge(
    draw: ImageDraw.ImageDraw,
    category: str,
    title: str,
    detail: str = "",
    y_pos: int = HUD_TOP_Y,
    composer: Optional["SceneComposer"] = None,
) -> BoundingBox:
    """
    Draw a professional 9:16 layout-aligned information-hierarchy HUD badge.
    Aligns to strict GRID_MARGIN_X (72px) with exact typography metrics.
    """
    font_cat = _load_font(20, bold=True)
    font_title = _load_font(34, bold=True)
    font_detail = _load_font(20, bold=False)

    badge_w = GRID_WIDTH
    pad_x, pad_y = 28, 16

    cat_h = SceneComposer.measure_text(category, font_cat)[1]
    title_h = SceneComposer.measure_text(title, font_title)[1]

    detail_lines: List[str] = []
    detail_h = 0
    if detail:
        _, detail_h, detail_lines = SceneComposer.measure_multiline(
            detail, font_detail, badge_w - 2 * pad_x
        )

    inner_h = cat_h + 8 + title_h + (10 + detail_h if detail else 0)
    badge_h = inner_h + 2 * pad_y

    x0 = GRID_MARGIN_X
    y0 = y_pos
    x1 = x0 + badge_w
    y1 = y0 + badge_h

    # Card background with subtle outline
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=16,
        fill=(10, 16, 28),
        outline=(32, 50, 80),
        width=2,
    )
    # Subtle top accent stripe
    draw.rounded_rectangle(
        [x0, y0, x1, y0 + 3],
        radius=2,
        fill=CYAN_ACCENT,
    )

    cursor_y = y0 + pad_y
    draw.text((x0 + pad_x, cursor_y), category.upper(), fill=CYAN_ACCENT, font=font_cat)
    cursor_y += cat_h + 8
    draw.text((x0 + pad_x, cursor_y), title.upper(), fill=COLOR_WHITE, font=font_title)
    cursor_y += title_h + 10

    if detail_lines:
        line_h_approx = detail_h // max(1, len(detail_lines))
        for dl in detail_lines:
            draw.text((x0 + pad_x, cursor_y), dl, fill=COLOR_TEXT_MUTED, font=font_detail)
            cursor_y += int(line_h_approx * 1.3)

    result_bb = BoundingBox(x0, y0, x1, y1, label="hud", priority=8)
    if composer is not None:
        composer._register(result_bb)
    return result_bb


def _draw_starfield(draw: ImageDraw.ImageDraw, seed: int = 42, count: int = 80):
    """Draw background stars. Used exclusively when context requires astronomy/deep space."""
    rng = random.Random(seed)
    for _ in range(count):
        sx = rng.randint(40, WIDTH - 40)
        sy = rng.randint(80, HEIGHT - 80)
        brightness = rng.randint(90, 220)
        r = 1 if brightness < 180 else 2
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(brightness, brightness, int(brightness * 1.15)))


def _draw_caption_bar(
    draw: ImageDraw.ImageDraw,
    text: str,
    composer: Optional["SceneComposer"] = None,
    y_bottom: Optional[int] = None,
    tag: str = "",
    animated_bounds: Optional[List[BoundingBox]] = None,
) -> BoundingBox:
    """
    Draw a 9:16 layout-aligned, collision-safe caption bar with word-wrap,
    optional semantic tag pill, and guaranteed clear visibility.
    """
    font_cap = _load_font(30, bold=True)
    font_tag = _load_font(18, bold=True)
    max_w = GRID_WIDTH - 48

    _, total_h, lines = SceneComposer.measure_multiline(text, font_cap, max_w)
    if not lines:
        lines = [text[:50]]
        total_h = 38

    line_h = total_h // max(1, len(lines))
    pad = 18
    clean_tag = tag.upper().strip() if tag else ""
    tag_h = 28 if clean_tag else 0
    box_h = total_h + (tag_h + 12 if clean_tag else 0) + 2 * pad
    x0_box = GRID_MARGIN_X
    x1_box = WIDTH - GRID_MARGIN_X

    if composer is not None and y_bottom is None:
        y0_box, y1_box = composer.compute_safe_caption_placement(box_h, animated_bounds)
    else:
        actual_bottom = y_bottom if y_bottom is not None else CAPTION_DEFAULT_BOTTOM
        y0_box = actual_bottom - box_h
        y1_box = actual_bottom

    # Refined dark panel with cyan accent border
    draw.rounded_rectangle(
        [x0_box, y0_box, x1_box, y1_box],
        radius=16,
        fill=(8, 13, 24),
        outline=(0, 180, 240),
        width=2,
    )

    cursor_y = y0_box + pad

    # Semantic Tag Pill
    if clean_tag:
        tw, th = SceneComposer.measure_text(clean_tag, font_tag)
        pill_w = tw + 28
        pill_x = (WIDTH - pill_w) // 2
        draw.rounded_rectangle(
            [pill_x, cursor_y, pill_x + pill_w, cursor_y + th + 8],
            radius=8,
            fill=(12, 22, 42),
            outline=GOLD_ACCENT,
            width=2,
        )
        draw.text((pill_x + 14, cursor_y + 3), clean_tag, fill=GOLD_ACCENT, font=font_tag)
        cursor_y += th + 12

    for line in lines:
        lw, _ = SceneComposer.measure_text(line, font_cap)
        lx = (WIDTH - lw) // 2
        draw.text((lx + 2, cursor_y + 2), line, fill=(0, 0, 0), font=font_cap)
        draw.text((lx, cursor_y), line, fill=COLOR_WHITE, font=font_cap)
        cursor_y += int(line_h * 1.3)

    result_bb = BoundingBox(x0_box, y0_box, x1_box, y1_box, label="caption", priority=6)
    if composer is not None and not any(r.label == "caption" for r in composer._registry):
        composer._register(result_bb)
    return result_bb


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 1: STRAIGHT LIGHT RAY (Normal light in flat spacetime)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_straight_ray(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes a star emitting a straight photon beam across flat space to an observer."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=101)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.HERO_VISUAL)
    _draw_starfield(draw, seed=101)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    # --- Layout: HUD top, caption bottom, visual in between ---
    hud_bb  = _draw_hud_badge(draw, "Physics Principle 01", "Normal Light Path",
                               detail="Photons travel in a straight Euclidean line through unwarped space.",
                               y_pos=80, composer=composer)
    cap_bb  = _draw_caption_bar(draw, "In flat spacetime, light travels in a perfectly straight line — always.",
                                 composer=composer, y_bottom=HEIGHT - 60)
    vis_bb  = composer.reserve_visual()

    # Center-Y of visual zone for the ray
    center_y = vis_bb.cy
    star_x   = vis_bb.x0 + 80
    obs_x    = vis_bb.x1 - 80

    # Flat-space grid (within visual zone)
    grid_top    = vis_bb.y0 + 40
    grid_bottom = vis_bb.y1 - 40
    for gy in range(grid_top, grid_bottom, 100):
        draw.line([(vis_bb.x0, gy), (vis_bb.x1, gy)], fill=GRID_COLOR, width=1)
    for gx in range(vis_bb.x0 + 60, vis_bb.x1, 120):
        draw.line([(gx, grid_top), (gx, grid_bottom)], fill=GRID_COLOR, width=1)

    # Star
    star_pulse = 1.0 + 0.08 * math.sin(t * math.pi * 6)
    sr = int(36 * star_pulse)
    for r in range(sr + 28, sr, -5):
        alpha = int(55 * (1 - (r - sr) / 28))
        draw.ellipse([star_x - r, center_y - r, star_x + r, center_y + r],
                     outline=(alpha, alpha, int(alpha * 1.5)), width=2)
    draw.ellipse([star_x - sr, center_y - sr, star_x + sr, center_y + sr],
                 fill=(255, 240, 180), outline=(255, 200, 80), width=3)
    font_lbl = _load_font(22, bold=True)
    draw.text((star_x - 50, center_y + sr + 14), "STAR (SOURCE)", fill=GOLD_ACCENT, font=font_lbl)

    # Observer reticle
    obs_r = 28
    draw.ellipse([obs_x - obs_r, center_y - obs_r, obs_x + obs_r, center_y + obs_r],
                 outline=CYAN_ACCENT, width=3)
    draw.line([(obs_x - obs_r - 10, center_y), (obs_x + obs_r + 10, center_y)], fill=CYAN_ACCENT, width=2)
    draw.line([(obs_x, center_y - obs_r - 10), (obs_x, center_y + obs_r + 10)], fill=CYAN_ACCENT, width=2)
    draw.text((obs_x - 44, center_y + obs_r + 14), "OBSERVER", fill=CYAN_ACCENT, font=font_lbl)

    # Animated photon ray
    ray_start = star_x + sr
    ray_end   = obs_x - obs_r
    current_ray_x = ray_start + int((ray_end - ray_start) * progress)
    draw.line([(ray_start, center_y), (current_ray_x, center_y)], fill=(0, 180, 255), width=7)
    draw.line([(ray_start, center_y), (current_ray_x, center_y)], fill=(240, 250, 255), width=2)
    draw.ellipse([current_ray_x - 11, center_y - 11, current_ray_x + 11, center_y + 11],
                 fill=WHITE, outline=CYAN_ACCENT, width=3)

    # Direction arrows
    if progress > 0.35:
        for ax in range(ray_start + 150, current_ray_x - 30, 180):
            draw.polygon([(ax, center_y - 7), (ax + 12, center_y), (ax, center_y + 7)], fill=CYAN_ACCENT)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 2: SPACETIME GRID WARPING (Mass appears & deforms spacetime)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_spacetime_warp(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes spacetime grid deforming into a gravitational well around a black hole."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=202)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.FULL_DIAGRAM)
    _draw_starfield(draw, seed=202)

    t = frame_idx / float(max(1, total_frames - 1))
    warp_progress = _ease_in_out(t)

    cx, cy = WIDTH // 2, 980
    max_distortion = 160 * warp_progress

    # Draw warped perspective grid lines
    # Horizontal grid lines that bend downward near center
    for grid_y in range(500, 1500, 100):
        pts = []
        for grid_x in range(80, WIDTH - 60, 45):
            dist_x = abs(grid_x - cx)
            dist_y = abs(grid_y - cy)
            r = math.sqrt(dist_x * dist_x + dist_y * dist_y) + 1.0
            
            # Gravitational well depression formula
            depression = (max_distortion * 320.0) / (r + 140.0)
            dy = depression if grid_y < cy else -depression * 0.4
            pts.append((grid_x, int(grid_y + dy)))
        if len(pts) > 1:
            draw.line(pts, fill=GRID_COLOR, width=2)

    # Vertical perspective grid lines that curve toward mass
    for grid_x in range(120, WIDTH - 80, 120):
        pts = []
        for grid_y in range(500, 1500, 50):
            dist_x = grid_x - cx
            dist_y = grid_y - cy
            r = math.sqrt(dist_x * dist_x + dist_y * dist_y) + 1.0
            pull = (max_distortion * 120.0) / (r + 160.0)
            dx = -pull if dist_x > 0 else pull
            pts.append((int(grid_x + dx), grid_y))
        if len(pts) > 1:
            draw.line(pts, fill=GRID_COLOR, width=2)

    # Central Black Hole & Event Horizon
    bh_radius = int(75 * min(1.0, warp_progress * 1.4))
    if bh_radius > 5:
        # Accretion glow corona
        for r in range(bh_radius + 45, bh_radius, -5):
            alpha = int(120 * (1 - (r - bh_radius) / 45))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(int(GOLD_ACCENT[0] * alpha / 120), int(GOLD_ACCENT[1] * alpha / 120), 0), width=3)

        # Photon Sphere ring
        draw.ellipse([cx - (bh_radius + 14), cy - (bh_radius + 14), cx + (bh_radius + 14), cy + (bh_radius + 14)], outline=GOLD_ACCENT, width=4)

        # Black Hole Shadow
        draw.ellipse([cx - bh_radius, cy - bh_radius, cx + bh_radius, cy + bh_radius], fill=(0, 0, 0), outline=(30, 30, 30), width=2)

    # HUD + caption (composer-aware)
    _draw_hud_badge(draw, "General Relativity", "Spacetime Curvature",
                    detail="Massive objects warp the fabric of space — light simply follows the curve.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "Mass tells spacetime how to curve. Spacetime tells light how to move.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 3: LIGHT TRAJECTORY BENDING (Photons curved by gravity)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_light_bending(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes light beam approaching a black hole and visibly bending along its curved geodesic."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=303)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.HERO_VISUAL)
    _draw_starfield(draw, seed=303)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    cx, cy = WIDTH // 2, 960
    bh_r = 85

    # Draw warped spacetime background rings
    for r in range(130, 480, 55):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GRID_COLOR, width=2)

    # Black hole in center
    # Golden accretion disk
    for r in range(bh_r + 40, bh_r, -4):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 160, 20), width=2)
    # Event horizon
    draw.ellipse([cx - bh_r, cy - bh_r, cx + bh_r, cy + bh_r], fill=(0, 0, 0), outline=(255, 210, 50), width=3)
    
    font_bh = _load_font(22, bold=True)
    draw.text((cx - 65, cy + bh_r + 14), "EVENT HORIZON", fill=GOLD_ACCENT, font=font_bh)

    # Calculate hyperbolic curved trajectory
    # Start: (120, 580) -> passes near (cx, cy - bh_r - 40) -> exits toward (WIDTH - 120, 1380)
    full_path: List[Tuple[int, int]] = []
    steps = 100
    for s in range(steps + 1):
        u = s / float(steps)
        # Quadratic/hyperbolic parametric curve
        x = int(120 + u * (WIDTH - 240))
        # Distance to center x
        dx = (x - cx) / 380.0
        # Deflection curve
        deflection = 380.0 / (1.0 + dx * dx * 2.8)
        y = int(580 + u * 420 + deflection)
        full_path.append((x, y))

    # Determine current drawn length based on progress
    visible_count = max(2, int(len(full_path) * progress))
    current_path = full_path[:visible_count]

    # Draw trajectory shadow / glow
    if len(current_path) > 1:
        draw.line(current_path, fill=(0, 180, 255), width=10)
        draw.line(current_path, fill=(255, 255, 255), width=4)

    # Head photon packet
    head_x, head_y = current_path[-1]
    draw.ellipse([head_x - 14, head_y - 14, head_x + 14, head_y + 14], fill=(255, 255, 255), outline=CYAN_ACCENT, width=3)

    # Deflection angle highlight arc
    if progress > 0.6:
        font_def = _load_font(28, bold=True)
        draw.text((cx - 160, cy - 240), "DEFLECTION ANGLE α", fill=GOLD_ACCENT, font=font_def)
        draw.line([(cx - 120, cy - 190), (cx + 120, cy - 190)], fill=GOLD_ACCENT, width=2)
        draw.polygon([(cx + 120, cy - 190), (cx + 105, cy - 196), (cx + 105, cy - 184)], fill=GOLD_ACCENT)

    _draw_hud_badge(draw, "Trajectory Bending", "Gravity Bends Light",
                    detail="Photons follow the shortest geodesic through curved spacetime.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "The photon's path curves — not because gravity pulls it, but because space itself bends.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 4: EINSTEIN RING & GRAVITATIONAL LENSING
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_einstein_ring(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes distant light lensed into a symmetric, glowing 360-degree Einstein Ring."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=404)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.ZOOM_IN)
    _draw_starfield(draw, seed=404)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    cx, cy = WIDTH // 2, 960
    lens_r = 160

    # Draw Central Foreground Galaxy / Black Hole Lens
    for r in range(80, 20, -10):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 22, 45), outline=GRID_COLOR, width=2)
    draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(0, 0, 0), outline=(60, 80, 120), width=2)

    # Animate Einstein Ring formation
    # Ring angle spans from 0 to 360 degrees as progress increases
    angle_sweep = int(360 * progress)
    if angle_sweep > 10:
        # Glowing multi-layer Einstein ring arcs
        for width_offset, col in [(8, (0, 140, 220)), (4, (0, 220, 255)), (2, (255, 255, 255))]:
            draw.arc(
                [cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r],
                start=0,
                end=angle_sweep,
                fill=col,
                width=width_offset,
            )

    # Distorted secondary arc highlights on opposite sides
    if progress > 0.4:
        for offset in [-lens_r - 20, lens_r + 20]:
            draw.ellipse([cx + offset - 10, cy - 10, cx + offset + 10, cy + 10], fill=(255, 240, 160))

    # Informative labels
    font_ring = _load_font(32, bold=True)
    if progress > 0.7:
        draw.text((cx - 130, cy + lens_r + 40), "EINSTEIN RING", fill=CYAN_ACCENT, font=font_ring)
        font_sub = _load_font(22, bold=False)
        draw.text((cx - 165, cy + lens_r + 85), "Perfect Gravitational Alignment", fill=MUTED_TEXT, font=font_sub)

    _draw_hud_badge(draw, "Observational Phenomenon", "The Einstein Ring",
                    detail="Perfect alignment of source, lens and observer creates a 360° light halo.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "When alignment is perfect, lensed light wraps 360° into a glowing Einstein Ring.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 5: SCALE COMPARISON (Black hole -> Galaxy -> Universe)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_scale_comparison(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes dramatic zoom pullback communicating immense astrophysical scale."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=505)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.COMPARISON)
    _draw_starfield(draw, seed=505)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    cx = WIDTH // 2
    # Three tier scale comparison cards
    scales = [
        ("EVENT HORIZON", "~30 KILOMETERS", "Size of a city", (255, 180, 20), 580),
        ("HOST GALAXY", "100,000 LIGHT YEARS", "Billions of star systems", (0, 220, 255), 880),
        ("GALAXY CLUSTER", "10 MILLION LIGHT YEARS", "Cosmic gravitational lens", (180, 140, 255), 1180),
    ]

    font_tier = _load_font(30, bold=True)
    font_val = _load_font(38, bold=True)
    font_desc = _load_font(22, bold=False)

    for i, (name, val, desc, color, y_card) in enumerate(scales):
        card_progress = _ease_in_out(max(0.0, min(1.0, (progress - i * 0.25) / 0.4)))
        if card_progress > 0:
            w_box = int(900 * card_progress)
            x0 = (WIDTH - w_box) // 2
            x1 = x0 + w_box
            y0 = y_card
            y1 = y0 + 180

            draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(12, 18, 36), outline=color, width=2)
            if card_progress > 0.6:
                draw.text((x0 + 35, y0 + 22), name, fill=color, font=font_tier)
                draw.text((x0 + 35, y0 + 64), val, fill=WHITE, font=font_val)
                draw.text((x0 + 35, y0 + 120), desc, fill=MUTED_TEXT, font=font_desc)

    _draw_hud_badge(draw, "Cosmic Proportions", "Astrophysical Scale",
                    detail="From a compact singularity to galaxy clusters spanning millions of light years.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "One black hole can contain the mass of billions of suns — compressed into a city-sized sphere.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 6: GENERIC SCIENTIFIC PROCESS DIAGRAM (Versatile Explainer)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_process_diagram(
    frame_idx: int,
    total_frames: int,
    title: str,
    steps: List[str],
) -> Image.Image:
    """Renders a multi-stage flow diagram with animated glowing pulses between stages."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=606)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.PROCESS_FLOW)
    _draw_starfield(draw, seed=606)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Process Visualization", title[:28],
                               detail="Step-by-step animated breakdown of the physical mechanism.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, f"Understanding {title}: each phase builds on the last.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    font_step = _load_font(22, bold=True)
    font_text = _load_font(28, bold=True)

    # Distribute nodes evenly within the visual zone
    max_steps  = min(4, len(steps))
    node_h     = min(120, (vis_bb.height - 20) // max_steps - 20)
    total_span = max_steps * (node_h + 20) - 20
    y_start    = vis_bb.y0 + (vis_bb.height - total_span) // 2
    gap        = node_h + 20
    node_w     = vis_bb.width

    active_idx = int(progress * max_steps)

    for i, step_text in enumerate(steps[:max_steps]):
        step_progress = _ease_in_out(max(0.0, min(1.0, (progress - i * (1.0 / max_steps)) / 0.35)))
        y_node = y_start + i * gap

        # Connector arrow
        if i > 0 and step_progress > 0.15:
            y_prev = y_node - gap + node_h
            draw.line([(WIDTH // 2, y_prev), (WIDTH // 2, y_node - 6)], fill=CYAN_ACCENT, width=3)
            draw.polygon([(WIDTH // 2, y_node - 6), (WIDTH // 2 - 10, y_node - 20),
                           (WIDTH // 2 + 10, y_node - 20)], fill=CYAN_ACCENT)

        if step_progress > 0:
            w_box = int(node_w * step_progress)
            x0_n  = (WIDTH - w_box) // 2
            x1_n  = x0_n + w_box
            is_active = (i == active_idx)
            draw.rounded_rectangle(
                [x0_n, y_node, x1_n, y_node + node_h],
                radius=14,
                fill=(10, 16, 32),
                outline=CYAN_ACCENT if is_active else (38, 56, 90),
                width=3 if is_active else 2,
            )
            if step_progress > 0.45:
                draw.text((x0_n + 24, y_node + 12), f"PHASE 0{i + 1}", fill=GOLD_ACCENT, font=font_step)
                draw.text((x0_n + 24, y_node + 46), step_text.upper()[:38], fill=WHITE, font=font_text)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 7: LIGHT APPROACHES THE GRAVITATIONAL FIELD
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_light_approaches(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes light beam approaching a massive black hole and entering its influence radius."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=707)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.HERO_VISUAL)
    _draw_starfield(draw, seed=707)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    cx, cy = WIDTH // 2 + 100, 1020
    bh_r = 75

    # Gravitational influence boundary (dashed or pulsating circle)
    influence_r = 280
    pulse = 1.0 + 0.04 * math.sin(t * math.pi * 4)
    ir = int(influence_r * pulse)
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=(0, 140, 200), width=2)
    font_field = _load_font(22, bold=True)
    draw.text((cx - 140, cy - ir - 30), "GRAVITATIONAL SPHERE", fill=CYAN_ACCENT, font=font_field)

    # Black hole in center-right
    for r in range(bh_r + 30, bh_r, -4):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 140, 20), width=2)
    draw.ellipse([cx - bh_r, cy - bh_r, cx + bh_r, cy + bh_r], fill=(0, 0, 0), outline=(255, 200, 40), width=3)

    # Incoming photon trajectory from top-left toward center
    start_x, start_y = 120, 520
    target_x, target_y = cx - 40, cy - bh_r - 20
    curr_x = int(start_x + (target_x - start_x) * progress)
    curr_y = int(start_y + (target_y - start_y) * progress)

    # Path line
    draw.line([(start_x, start_y), (curr_x, curr_y)], fill=(0, 180, 255), width=8)
    draw.line([(start_x, start_y), (curr_x, curr_y)], fill=(255, 255, 255), width=3)

    # Leading photon packet
    draw.ellipse([curr_x - 14, curr_y - 14, curr_x + 14, curr_y + 14], fill=(255, 255, 255), outline=CYAN_ACCENT, width=3)

    # Approach velocity vector label
    if progress > 0.3:
        font_vec = _load_font(26, bold=True)
        draw.text((curr_x + 20, curr_y - 30), "APPROACH TRAJECTORY", fill=GOLD_ACCENT, font=font_vec)

    _draw_hud_badge(draw, "Relativistic Approach", "Light Enters Gravity Well",
                    detail="As photons near extreme mass, spacetime curvature starts dictating their path.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "The closer to the black hole, the stronger the gravitational influence on the photon's path.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 8: COMPARISON (Newton Flat Space vs Einstein Curved Spacetime)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_comparison(frame_idx: int, total_frames: int) -> Image.Image:
    """Side-by-side or dual comparison: Newtonian flat space vs Einsteinian curved spacetime."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=808)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.COMPARISON)
    _draw_starfield(draw, seed=808)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Theoretical Comparison", "Newton vs. Einstein",
                               detail="Classical physics treated space as a rigid stage. General Relativity revealed space is dynamic.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, "Newton thought space was flat and rigid. Einstein proved space itself is curved by mass.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    font_hd = _load_font(28, bold=True)
    font_sub = _load_font(22, bold=False)

    font_sub = _load_font(20, bold=False)

    # Split visual zone into two equal stacked panels
    panel_h  = (vis_bb.height - 24) // 2
    p1_y0    = vis_bb.y0
    p2_y0    = vis_bb.y0 + panel_h + 24

    # Card 1: Newtonian Flat Space
    draw.rounded_rectangle([vis_bb.x0, p1_y0, vis_bb.x1, p1_y0 + panel_h],
                            radius=14, fill=(10, 16, 32), outline=(50, 70, 110), width=2)
    draw.text((vis_bb.x0 + 24, p1_y0 + 16), "NEWTONIAN FRAMEWORK", fill=(180, 200, 230), font=font_hd)
    draw.text((vis_bb.x0 + 24, p1_y0 + 54), "Flat space — light travels straight.", fill=MUTED_TEXT, font=font_sub)

    ray1_start = vis_bb.x0 + 24
    ray1_mid   = p1_y0 + int(panel_h * 0.65)
    ray1_curr  = int(ray1_start + (vis_bb.width - 48) * progress)
    draw.line([(ray1_start, ray1_mid), (ray1_curr, ray1_mid)], fill=(0, 180, 255), width=5)
    draw.ellipse([ray1_curr - 9, ray1_mid - 9, ray1_curr + 9, ray1_mid + 9], fill=WHITE)
    draw.text((WIDTH // 2 - 72, ray1_mid + 18), "DEFLECTION = 0°", fill=(140, 160, 190), font=font_sub)

    # Card 2: General Relativity
    draw.rounded_rectangle([vis_bb.x0, p2_y0, vis_bb.x1, p2_y0 + panel_h],
                            radius=14, fill=(12, 20, 42), outline=CYAN_ACCENT, width=2)
    draw.text((vis_bb.x0 + 24, p2_y0 + 16), "GENERAL RELATIVITY", fill=GOLD_ACCENT, font=font_hd)
    draw.text((vis_bb.x0 + 24, p2_y0 + 54), "Curved space — light follows geodesic.", fill=MUTED_TEXT, font=font_sub)

    mass_cx = WIDTH // 2
    mass_cy = p2_y0 + int(panel_h * 0.62)
    draw.ellipse([mass_cx - 28, mass_cy - 28, mass_cx + 28, mass_cy + 28],
                 fill=(0, 0, 0), outline=GOLD_ACCENT, width=3)

    pts2: List[Tuple[int, int]] = []
    n_steps = 60
    for s in range(int(n_steps * progress) + 1):
        u = s / float(n_steps)
        x = int(vis_bb.x0 + 24 + u * (vis_bb.width - 48))
        dx = (x - mass_cx) / 180.0
        dy = int(100.0 / (1.0 + dx * dx * 3.2))
        pts2.append((x, mass_cy - 60 + dy))
    if len(pts2) > 1:
        draw.line(pts2, fill=(0, 220, 255), width=5)
        draw.ellipse([pts2[-1][0] - 9, pts2[-1][1] - 9,
                      pts2[-1][0] + 9, pts2[-1][1] + 9], fill=WHITE)

    draw.text((WIDTH // 2 - 100, p2_y0 + panel_h - 46), "α = 4GM / rc²", fill=CYAN_ACCENT, font=font_sub)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 9: DATA METRICS & FORMULA READOUT
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_data_metric(frame_idx: int, total_frames: int) -> Image.Image:
    """Dynamic HUD readout of astrophysical metrics, formulas, and cosmic constants."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=909)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.PROCESS_FLOW)
    _draw_starfield(draw, seed=909)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Astrophysical Metrics", "The Relativistic Constants",
                               detail="Equations validated by modern orbital and space telescope measurements.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, "These constants are not approximations — they are exact physical laws of the universe.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    metrics = [
        ("SPEED OF LIGHT (c)", "299,792,458 m/s",   "Universal speed of information",           GOLD_ACCENT),
        ("SCHWARZSCHILD RADIUS", "Rs = 2GM / c²",   "Radius where escape velocity = c",          CYAN_ACCENT),
        ("LIGHT DEFLECTION",    "θ = 4GM / rc²",    "Einstein's 1915 gravitational prediction",  (190, 150, 255)),
    ]

    font_m_title = _load_font(24, bold=True)
    font_m_val   = _load_font(34, bold=True)
    font_m_desc  = _load_font(20, bold=False)

    card_h   = min(170, (vis_bb.height - 20) // 3 - 16)
    gap      = (vis_bb.height - 3 * card_h) // 4

    for i, (m_lbl, m_val, m_desc, col) in enumerate(metrics):
        card_t = _ease_in_out(max(0.0, min(1.0, (progress - i * 0.22) / 0.45)))
        if card_t > 0:
            y0_c = vis_bb.y0 + gap + i * (card_h + gap)
            w_c  = int(vis_bb.width * card_t)
            x0_c = (WIDTH - w_c) // 2
            x1_c = x0_c + w_c
            draw.rounded_rectangle([x0_c, y0_c, x1_c, y0_c + card_h],
                                    radius=14, fill=(10, 16, 32), outline=col, width=2)
            if card_t > 0.5:
                draw.text((x0_c + 28, y0_c + 14), m_lbl, fill=col, font=font_m_title)
                draw.text((x0_c + 28, y0_c + 54), m_val, fill=WHITE, font=font_m_val)
                draw.text((x0_c + 28, y0_c + 110), m_desc, fill=MUTED_TEXT, font=font_m_desc)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 10: CONCEPTUAL PAYOFF / TEXT EMPHASIS (Space Itself Is Curved)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_text_emphasis(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes the core payoff with radiating gravitational ripples and kinetic typography."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=1010)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.CINEMATIC_CAPTION)
    _draw_starfield(draw, seed=1010)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    cx, cy = WIDTH // 2, 880

    # Pulsating gravitational wave ripples expanding outward
    for i in range(5):
        wave_phase = (progress * 2.0 + i * 0.25) % 1.0
        r_wave = int(80 + wave_phase * 420)
        alpha = int(180 * (1.0 - wave_phase))
        if alpha > 0 and r_wave > 80:
            draw.ellipse(
                [cx - r_wave, cy - r_wave, cx + r_wave, cy + r_wave],
                outline=(0, min(255, int(alpha * 1.2)), alpha),
                width=3,
            )

    # Central Singularity / Accretion Core
    core_r = 50
    draw.ellipse([cx - core_r - 20, cy - core_r - 20, cx + core_r + 20, cy + core_r + 20], outline=GOLD_ACCENT, width=3)
    draw.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(0, 0, 0), outline=(255, 255, 255), width=2)

    # Kinetic Typography Payoff Box
    font_main = _load_font(52, bold=True)
    font_sub = _load_font(28, bold=True)
    font_quote = _load_font(24, bold=False)

    card_y = 1240
    draw.rounded_rectangle([70, card_y, WIDTH - 70, card_y + 320], radius=20, fill=(8, 14, 28), outline=CYAN_ACCENT, width=3)

    draw.text((WIDTH // 2 - 290, card_y + 40), "SPACE ITSELF IS CURVED", fill=CYAN_ACCENT, font=font_main)
    draw.text((WIDTH // 2 - 260, card_y + 125), "GRAVITY IS NOT A FORCE, IT IS GEOMETRY", fill=GOLD_ACCENT, font=font_sub)
    draw.text((WIDTH // 2 - 320, card_y + 195), "“Matter tells spacetime how to curve, and spacetime", fill=WHITE, font=font_quote)
    draw.text((WIDTH // 2 - 240, card_y + 240), "tells light how to move.” — John Wheeler", fill=MUTED_TEXT, font=font_quote)

    _draw_hud_badge(draw, "Final Revelation", "The Geometry of Spacetime",
                    detail="Photons travel straight in their local frame — but space itself is curved.",
                    y_pos=80, composer=composer)
    _draw_caption_bar(draw, "Gravity is not a force — it is the curvature of spacetime itself. Light simply follows.",
                       composer=composer, y_bottom=HEIGHT - 60)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 11: RADIO WAVES & WIRELESS PROPAGATION (Wi-Fi Signal)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_radio_waves(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes Wi-Fi router emitting concentric pulsating electromagnetic radio waves to client devices."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=1111)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.HERO_VISUAL)
    _draw_starfield(draw, seed=1111)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Electromagnetic Spectrum", "Wireless Radio Waves",
                               detail="Wi-Fi converts binary bits into high-frequency gigahertz radio waves.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, "Your router broadcasts invisible radio waves in all directions — 2.4 GHz and 5 GHz simultaneously.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    router_x = WIDTH // 2
    # Place router in lower portion of visual zone
    router_y = vis_bb.y0 + int(vis_bb.height * 0.62)

    # Expanding electromagnetic wavefronts
    for i in range(6):
        phase  = (t * 2.2 + i * 0.18) % 1.0
        r_wave = int(70 + phase * 420)
        alpha  = int(220 * (1.0 - phase))
        if r_wave > 80 and alpha > 10:
            draw.arc(
                [router_x - r_wave, router_y - r_wave - 50, router_x + r_wave, router_y + r_wave - 50],
                start=195, end=345,
                fill=(0, min(255, int(alpha * 1.1)), alpha),
                width=4,
            )

    # Router body
    w_box, h_box = 260, 90
    rx0 = router_x - w_box // 2
    ry0 = router_y
    draw.rounded_rectangle([rx0, ry0, rx0 + w_box, ry0 + h_box],
                            radius=12, fill=(12, 18, 36), outline=CYAN_ACCENT, width=3)
    draw.line([(rx0 + 38, ry0), (rx0 + 18, ry0 - 100)], fill=CYAN_ACCENT, width=5)
    draw.line([(rx0 + w_box - 38, ry0), (rx0 + w_box - 18, ry0 - 100)], fill=CYAN_ACCENT, width=5)
    draw.ellipse([rx0 + 13, ry0 - 108, rx0 + 23, ry0 - 93], fill=WHITE)
    draw.ellipse([rx0 + w_box - 23, ry0 - 108, rx0 + w_box - 13, ry0 - 93], fill=WHITE)
    for lx in range(rx0 + 55, rx0 + w_box - 55, 34):
        draw.ellipse([lx - 4, ry0 + 45, lx + 4, ry0 + 55],
                     fill=(0, 255, 180) if (frame_idx % 8 < 5) else (0, 100, 70))
    font_r = _load_font(22, bold=True)
    draw.text((router_x - 72, ry0 + 18), "WI-FI ROUTER", fill=WHITE, font=font_r)

    # Receiving device near top of visual zone (collision-safe)
    phone_y = vis_bb.y0 + 20
    phone_x = WIDTH // 2
    draw.rounded_rectangle([phone_x - 60, phone_y, phone_x + 60, phone_y + 120],
                            radius=10, fill=(14, 22, 44), outline=GOLD_ACCENT, width=2)
    font_ph = _load_font(18, bold=True)
    draw.text((phone_x - 44, phone_y + 28), "RECEIVER",  fill=GOLD_ACCENT, font=font_ph)
    draw.text((phone_x - 38, phone_y + 62), "DECODING",  fill=WHITE,       font=font_ph)

    # Frequency callout (placed safely below router, above caption)
    freq_y = min(ry0 + h_box + 14, cap_bb.y0 - 42)
    if freq_y < cap_bb.y0 - 12:
        font_fq = _load_font(22, bold=True)
        draw.text((WIDTH // 2 - 120, freq_y), "2.4 GHz & 5 GHz RF CARRIER", fill=CYAN_ACCENT, font=font_fq)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 12: BINARY PACKETS & DATA MODULATION
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_binary_packets(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes binary 1s and 0s modulated onto sinusoidal radio carrier wave."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=1212)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.FULL_DIAGRAM)
    _draw_starfield(draw, seed=1212)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Signal Modulation", "Binary Data to Radio Pulses",
                               detail="Modulation varies wave height & phase to carry billions of bits per second.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, "Each 1 and 0 in your data modifies the shape of a radio wave — that's how Wi-Fi works.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    # Carrier wave drawing across visual zone
    mid_y = 960
    wave_pts: List[Tuple[int, int]] = []
    bit_labels = ["1", "0", "1", "1", "0", "1", "0", "0", "1", "1"]
    
    for x in range(80, WIDTH - 80, 8):
        u = (x - 80) / float(WIDTH - 160)
        # Sine wave modulated by phase
        phase_shift = math.sin((u * 12.0 - t * 4.0) * math.pi)
        y = int(mid_y + phase_shift * 90)
        wave_pts.append((x, y))

    if len(wave_pts) > 1:
        draw.line(wave_pts, fill=(0, 140, 220), width=8)
        draw.line(wave_pts, fill=(240, 255, 255), width=3)

    # Binary bits hovering on peaks
    font_bit = _load_font(32, bold=True)
    for i, b in enumerate(bit_labels):
        bx = int(140 + i * 80)
        if bx < WIDTH - 120:
            by = int(mid_y - 140 + 20 * math.sin((i - t * 3.0) * math.pi))
            col = GOLD_ACCENT if b == "1" else CYAN_ACCENT
            draw.rounded_rectangle([bx - 22, by - 22, bx + 22, by + 22], radius=8, fill=(10, 16, 32), outline=col, width=2)
            draw.text((bx - 8, by - 18), b, fill=WHITE, font=font_bit)

    # Demodulation HUD box at bottom
    box_y = 1220
    draw.rounded_rectangle([90, box_y, WIDTH - 90, box_y + 220], radius=16, fill=(10, 18, 38), outline=CYAN_ACCENT, width=2)
    font_card = _load_font(28, bold=True)
    font_sub = _load_font(22, bold=False)
    draw.text((125, box_y + 25), "QUADRATURE AMPLITUDE MODULATION (QAM)", fill=CYAN_ACCENT, font=font_card)
    draw.text((125, box_y + 70), "Carrier Wave Frequency: 5.180 GHz (Channel 36)", fill=WHITE, font=font_sub)
    draw.text((125, box_y + 115), "Data Stream: 01101001 01100110 01101001 (Encoded Payload)", fill=GOLD_ACCENT, font=font_sub)
    draw.text((125, box_y + 160), "Bitrate: 866.7 Mbps | Latency: 4 ms", fill=MUTED_TEXT, font=font_sub)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 13: FREQUENCY SPECTRUM (2.4 GHz vs 5 GHz)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_frequency_spectrum(frame_idx: int, total_frames: int) -> Image.Image:
    """Visualizes comparison between 2.4 GHz and 5 GHz wireless bands."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient_bg(img, seed=1313)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.COMPARISON)
    _draw_starfield(draw, seed=1313)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    hud_bb = _draw_hud_badge(draw, "Spectrum Comparison", "2.4 GHz vs. 5 GHz Bands",
                               detail="Higher frequencies carry more data but have shorter physical range.",
                               y_pos=80, composer=composer)
    cap_bb = _draw_caption_bar(draw, "2.4 GHz travels farther through walls. 5 GHz is faster but fades quickly.",
                                composer=composer, y_bottom=HEIGHT - 60)
    vis_bb = composer.reserve_visual()

    font_hd = _load_font(28, bold=True)
    font_sub = _load_font(22, bold=False)

    font_sub = _load_font(19, bold=False)

    panel_h = (vis_bb.height - 20) // 2 - 8
    p1_y0   = vis_bb.y0
    p2_y0   = vis_bb.y0 + panel_h + 20

    # Card 1: 2.4 GHz
    draw.rounded_rectangle([vis_bb.x0, p1_y0, vis_bb.x1, p1_y0 + panel_h],
                            radius=14, fill=(10, 16, 32), outline=GOLD_ACCENT, width=2)
    draw.text((vis_bb.x0 + 22, p1_y0 + 14), "2.4 GHz — LONGER RANGE",              fill=GOLD_ACCENT, font=font_hd)
    draw.text((vis_bb.x0 + 22, p1_y0 + 52), "~12.5 cm wavelength · Penetrates walls · ~450 Mbps", fill=MUTED_TEXT, font=font_sub)
    w1_pts: List[Tuple[int, int]] = []
    wave_mid1 = p1_y0 + int(panel_h * 0.72)
    for x in range(vis_bb.x0 + 20, vis_bb.x1 - 20, 5):
        u = (x - vis_bb.x0) / float(vis_bb.width)
        y = int(wave_mid1 + math.sin((u * 4.0 - t * 2.0) * math.pi * 2) * 44)
        w1_pts.append((x, y))
    if w1_pts:
        draw.line(w1_pts, fill=GOLD_ACCENT, width=5)

    # Card 2: 5 GHz
    draw.rounded_rectangle([vis_bb.x0, p2_y0, vis_bb.x1, p2_y0 + panel_h],
                            radius=14, fill=(12, 20, 42), outline=CYAN_ACCENT, width=2)
    draw.text((vis_bb.x0 + 22, p2_y0 + 14), "5.0 GHz — HIGH SPEED",                fill=CYAN_ACCENT, font=font_hd)
    draw.text((vis_bb.x0 + 22, p2_y0 + 52), "~6 cm wavelength · Wall-limited · 1300+ Mbps",      fill=MUTED_TEXT, font=font_sub)
    w2_pts: List[Tuple[int, int]] = []
    wave_mid2 = p2_y0 + int(panel_h * 0.72)
    for x in range(vis_bb.x0 + 20, vis_bb.x1 - 20, 4):
        u = (x - vis_bb.x0) / float(vis_bb.width)
        y = int(wave_mid2 + math.sin((u * 12.0 - t * 4.0) * math.pi * 2) * 34)
        w2_pts.append((x, y))
    if w2_pts:
        draw.line(w2_pts, fill=CYAN_ACCENT, width=5)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL VISUAL STORYTELLING RENDERERS (V3 GLOBAL ARCHETYPES)
# ─────────────────────────────────────────────────────────────────────────────

def _render_frame_universal_physical_demo(
    frame_idx: int,
    total_frames: int,
    title: str = "Physical Mechanics",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Physical Demonstration (Type B).
    Visualizes an object reacting dynamically to applied forces, thrust, gravity, or momentum.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=707)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.PHYSICAL_DEMO)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Mechanical Entity").strip()
    action = str(meta.get("visual_action") or "produces directional force").strip()
    tag = str(meta.get("supporting_text") or "").strip()
    claim = str(meta.get("core_claim") or narration or f"{subject} demonstrates physical dynamics").strip()

    # Determine force and physical dynamics direction
    combined = f"{subject} {action} {tag} {claim}".lower()
    is_downward = any(w in combined for w in ["gravity", "down", "fall", "pull", "drop", "sink", "weight"])
    is_upward   = any(w in combined for w in ["lift", "rise", "ascend", "up", "soar", "elevat"])
    is_backward = any(w in combined for w in ["drag", "resist", "friction", "brake", "backward"])
    is_light    = any(w in combined for w in ["light", "ray", "photon", "focus", "beam", "lens"])
    is_aperture = any(w in combined for w in ["aperture", "iris", "diaphragm", "f-stop"])
    is_charge   = any(w in combined for w in ["electron", "charge", "pixel", "well", "sensor", "photodiode"])

    if not tag:
        if is_downward:
            tag = "GRAVITY ↓"
        elif is_upward:
            tag = "LIFT ↑"
        elif is_backward:
            tag = "DRAG ←"
        elif is_light:
            tag = "LIGHT PROPAGATION →"
        elif is_aperture:
            tag = "APERTURE CALIBRATION"
        elif is_charge:
            tag = "CHARGE ACCUMULATION"
        else:
            tag = "MOMENTUM → FORWARD"

    hud_bb = _draw_hud_badge(draw, "Physical Demonstration", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    cx, cy = vis_bb.cx, vis_bb.cy

    # Compute object displacement along force vector
    max_disp = 160
    if is_downward:
        dx, dy = 0, int(max_disp * progress)
    elif is_upward:
        dx, dy = 0, -int(max_disp * progress)
    elif is_backward:
        dx, dy = -int(max_disp * progress), 0
    else:  # Forward / Beam
        dx, dy = int(max_disp * progress), 0

    obj_x = cx + dx
    obj_y = cy + dy
    obj_w, obj_h = 240, 110

    # Calculate animated visual bounds at key intervals for collision avoidance
    animated_bounds = [
        BoundingBox(cx - obj_w // 2, cy - obj_h // 2, cx + obj_w // 2, cy + obj_h // 2, "visual", 10),
        BoundingBox(cx + dx // 2 - obj_w // 2, cy + dy // 2 - obj_h // 2, cx + dx // 2 + obj_w // 2, cy + dy // 2 + obj_h // 2, "visual", 10),
        BoundingBox(obj_x - obj_w // 2, obj_y - obj_h // 2, obj_x + obj_w // 2, obj_y + obj_h // 2, "visual", 10),
    ]

    # Coordinate reference grid
    for gx in range(vis_bb.x0 + 40, vis_bb.x1, 140):
        draw.line([(gx, vis_bb.y0 + 20), (gx, vis_bb.y1 - 20)], fill=(18, 28, 52), width=1)
    for gy in range(vis_bb.y0 + 40, vis_bb.y1, 120):
        draw.line([(vis_bb.x0 + 20, gy), (vis_bb.x1 - 20, gy)], fill=(18, 28, 52), width=1)

    # Reaction trail (exhaust / wake / light beam)
    trail_len = int(180 * progress)
    if is_downward:
        trail_pts = [(obj_x, obj_y - obj_h // 2), (obj_x, obj_y - obj_h // 2 - trail_len)]
    elif is_upward:
        trail_pts = [(obj_x, obj_y + obj_h // 2), (obj_x, obj_y + obj_h // 2 + trail_len)]
    elif is_backward:
        trail_pts = [(obj_x + obj_w // 2, obj_y), (obj_x + obj_w // 2 + trail_len, obj_y)]
    else:
        trail_pts = [(obj_x - obj_w // 2, obj_y), (obj_x - obj_w // 2 - trail_len, obj_y)]

    if trail_len > 10:
        draw.line(trail_pts, fill=(0, 140, 220), width=6)
        draw.line(trail_pts, fill=(240, 255, 255), width=2)
        for p in range(5):
            u_p = (progress * 3.0 + p * 0.2) % 1.0
            sp_x = trail_pts[0][0] + int((trail_pts[1][0] - trail_pts[0][0]) * u_p)
            sp_y = trail_pts[0][1] + int((trail_pts[1][1] - trail_pts[0][1]) * u_p)
            draw.ellipse([sp_x - 4, sp_y - 4, sp_x + 4, sp_y + 4], fill=GOLD_ACCENT)

    # Subject backdrop for maximum contrast
    _draw_subject_backdrop(draw, BoundingBox(obj_x - obj_w // 2 - 12, obj_y - obj_h // 2 - 12,
                                             obj_x + obj_w // 2 + 12, obj_y + obj_h // 2 + 12, "subject_pad", 5))

    # Primary Physical Subject Body
    draw.rounded_rectangle(
        [obj_x - obj_w // 2, obj_y - obj_h // 2, obj_x + obj_w // 2, obj_y + obj_h // 2],
        radius=18,
        fill=(12, 20, 42),
        outline=CYAN_ACCENT,
        width=3,
    )
    draw.ellipse([obj_x - 22, obj_y - 22, obj_x + 22, obj_y + 22], fill=(0, 210, 255), outline=WHITE, width=2)

    font_obj = _load_font(22, bold=True)
    draw.text((obj_x - obj_w // 2 + 20, obj_y + obj_h // 2 - 32), subject.upper()[:16], fill=WHITE, font=font_obj)

    # Active Force / Propagation Vector Arrow
    arrow_len = 140
    if is_downward:
        ax0, ay0 = obj_x, obj_y + obj_h // 2
        ax1, ay1 = obj_x, ay0 + arrow_len
        draw.line([(ax0, ay0), (ax1, ay1)], fill=GOLD_ACCENT, width=6)
        draw.polygon([(ax1, ay1), (ax1 - 14, ay1 - 22), (ax1 + 14, ay1 - 22)], fill=GOLD_ACCENT)
        draw.text((ax1 + 20, ay0 + arrow_len // 2 - 10), "GRAVITY VECTOR", fill=GOLD_ACCENT, font=font_obj)
    elif is_upward:
        ax0, ay0 = obj_x, obj_y - obj_h // 2
        ax1, ay1 = obj_x, ay0 - arrow_len
        draw.line([(ax0, ay0), (ax1, ay1)], fill=CYAN_ACCENT, width=6)
        draw.polygon([(ax1, ay1), (ax1 - 14, ay1 + 22), (ax1 + 14, ay1 + 22)], fill=CYAN_ACCENT)
        draw.text((ax1 + 20, ay1 + arrow_len // 2 - 10), "LIFT VECTOR", fill=CYAN_ACCENT, font=font_obj)
    elif is_backward:
        ax0, ay0 = obj_x - obj_w // 2, obj_y
        ax1, ay1 = ax0 - arrow_len, obj_y
        draw.line([(ax0, ay0), (ax1, ay1)], fill=GOLD_ACCENT, width=6)
        draw.polygon([(ax1, ay1), (ax1 + 22, ay1 - 14), (ax1 + 22, ay1 + 14)], fill=GOLD_ACCENT)
        draw.text((ax1 - 120, ay1 - 32), "DRAG VECTOR", fill=GOLD_ACCENT, font=font_obj)
    else:  # Forward / Light beam / Charge propagation
        ax0, ay0 = obj_x + obj_w // 2, obj_y
        ax1, ay1 = ax0 + arrow_len, obj_y
        draw.line([(ax0, ay0), (ax1, ay1)], fill=GOLD_ACCENT, width=6)
        draw.polygon([(ax1, ay1), (ax1 - 22, ay1 - 14), (ax1 - 22, ay1 + 14)], fill=GOLD_ACCENT)
        vec_name = "PHOTON PROPAGATION" if is_light else "CHARGE VECTOR" if is_charge else "APERTURE VECTOR" if is_aperture else "THRUST VECTOR"
        draw.text((ax0 + 20, ay0 - 34), vec_name, fill=GOLD_ACCENT, font=font_obj)

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag, animated_bounds=animated_bounds)
    return img


def _render_frame_universal_transformation(
    frame_idx: int,
    total_frames: int,
    title: str = "State Transformation",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Transformation (Type D).
    Visualizes fluid, continuous conversion across an energetic conversion boundary without template cards.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=808)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.TRANSFORMATION)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Transformation").strip()
    tag = str(meta.get("supporting_text") or "ACTIVE CONVERSION").strip()
    claim = str(meta.get("core_claim") or narration or f"Energy transforms dynamically").strip()

    hud_bb = _draw_hud_badge(draw, "Energy Transformation", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    cx, cy = vis_bb.cx, vis_bb.cy

    # Ambient backdrop behind transformation zone
    conv_bb = BoundingBox(vis_bb.x0 + 20, cy - 220, vis_bb.x1 - 20, cy + 220, "conversion_zone", 10)
    _draw_subject_backdrop(draw, conv_bb)

    # Central conversion barrier / depletion interface
    barrier_w = 40
    draw.rounded_rectangle([cx - barrier_w // 2, cy - 180, cx + barrier_w // 2, cy + 180],
                           radius=12, fill=(16, 26, 48), outline=CYAN_ACCENT, width=2)
    # Pulsing conversion energy field
    for i in range(3):
        pulse_alpha = int(140 * (1.0 - (progress + i * 0.33) % 1.0))
        draw.line([(cx, cy - 170), (cx, cy + 170)],
                  fill=(0, int(210 * (pulse_alpha / 140.0)), int(255 * (pulse_alpha / 140.0))), width=3)

    # Left: Input Source Stream (e.g. Photons / Light Waves / Initial State)
    left_cx = cx - 240
    draw.ellipse([left_cx - 60, cy - 60, left_cx + 60, cy + 60], fill=(12, 22, 42), outline=CYAN_ACCENT, width=2)
    draw.ellipse([left_cx - 24, cy - 24, left_cx + 24, cy + 24], fill=(0, 180, 240))
    font_lbl = _load_font(20, bold=True)
    draw.text((left_cx - 50, cy + 80), "INPUT STATE", fill=CYAN_ACCENT, font=font_lbl)

    # Right: Converted Output Stream (e.g. Electric Charges / Processed Signal / Final State)
    right_cx = cx + 240
    right_col = GOLD_ACCENT if progress > 0.4 else (45, 60, 90)
    draw.ellipse([right_cx - 60, cy - 60, right_cx + 60, cy + 60],
                 fill=(28, 24, 16) if progress > 0.4 else (12, 16, 28), outline=right_col, width=2)
    if progress > 0.4:
        draw.ellipse([right_cx - 24, cy - 24, right_cx + 24, cy + 24], fill=GOLD_ACCENT)
    draw.text((right_cx - 65, cy + 80), "CONVERTED STATE", fill=right_col, font=font_lbl)

    # Crossing particles streaming across the barrier
    span_x0 = left_cx + 60
    span_x1 = right_cx - 60
    for p in range(6):
        u_p = (progress * 2.2 + p * 0.16) % 1.0
        px = span_x0 + int((span_x1 - span_x0) * u_p)
        py = cy + int(math.sin(u_p * math.pi * 4 + p) * 20)
        # Particle changes color/nature upon crossing center threshold
        if px < cx:
            p_color = (0, 220, 255)
            p_r = 5
        else:
            p_color = GOLD_ACCENT
            p_r = 7
        draw.ellipse([px - p_r, py - p_r, px + p_r, py + p_r], fill=p_color)

    # Bottom conversion gauge
    gauge_y = cy + 140
    gauge_w = vis_bb.width - 80
    gauge_x0 = vis_bb.x0 + 40
    draw.rounded_rectangle([gauge_x0, gauge_y, gauge_x0 + gauge_w, gauge_y + 20],
                           radius=10, fill=(10, 16, 30), outline=(32, 48, 76), width=2)
    fill_w = int(gauge_w * progress)
    if fill_w > 8:
        draw.rounded_rectangle([gauge_x0, gauge_y, gauge_x0 + fill_w, gauge_y + 20],
                               radius=10, fill=GOLD_ACCENT)

    font_pct = _load_font(20, bold=True)
    draw.text((cx - 60, gauge_y + 30), f"{int(progress * 100)}% CONVERTED", fill=GOLD_ACCENT, font=font_pct)

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag)
    return img


def _render_frame_universal_object_interaction(
    frame_idx: int,
    total_frames: int,
    title: str = "Object Interaction",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Object Interaction (Type K).
    Visualizes packets, signals, or physical contact between two interacting objects.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=909)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.OBJECT_INTERACTION)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Transmission").strip()
    tag = str(meta.get("supporting_text") or "PACKET SENT → RECEIVED").strip()
    claim = str(meta.get("core_claim") or narration or f"Objects exchange signals seamlessly").strip()

    hud_bb = _draw_hud_badge(draw, "Object Interaction", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    node_r = 70
    source_x, source_y = vis_bb.cx - 240, vis_bb.cy - 30
    target_x, target_y = vis_bb.cx + 240, vis_bb.cy - 30

    font_n = _load_font(22, bold=True)
    font_sub = _load_font(18, bold=False)

    # Ambient backdrops behind both nodes
    _draw_subject_backdrop(draw, BoundingBox(source_x - node_r - 10, source_y - node_r - 10,
                                             source_x + node_r + 10, source_y + node_r + 10))
    _draw_subject_backdrop(draw, BoundingBox(target_x - node_r - 10, target_y - node_r - 10,
                                             target_x + node_r + 10, target_y + node_r + 10))

    # Source node
    draw.ellipse([source_x - node_r, source_y - node_r, source_x + node_r, source_y + node_r],
                 fill=(12, 22, 46), outline=CYAN_ACCENT, width=3)
    draw.text((source_x - 38, source_y - 14), "SOURCE", fill=WHITE, font=font_n)
    draw.text((source_x - 48, source_y + 14), "EMITTING", fill=CYAN_ACCENT, font=font_sub)

    is_received = (progress > 0.75)
    target_col = GOLD_ACCENT if is_received else (45, 65, 95)
    draw.ellipse([target_x - node_r, target_y - node_r, target_x + node_r, target_y + node_r],
                 fill=(22, 28, 48) if is_received else (10, 14, 26), outline=target_col, width=3)
    draw.text((target_x - 38, target_y - 14), "TARGET", fill=WHITE, font=font_n)
    draw.text((target_x - 52, target_y + 14), "DETECTED" if is_received else "AWAITING",
              fill=GOLD_ACCENT if is_received else MUTED_TEXT, font=font_sub)

    if is_received:
        rec_phase = (progress - 0.75) / 0.25
        rip_r = int(node_r + rec_phase * 60)
        draw.ellipse([target_x - rip_r, target_y - rip_r, target_x + rip_r, target_y + rip_r],
                     outline=GOLD_ACCENT, width=2)

    # Bus line
    for x in range(source_x + node_r + 10, target_x - node_r - 10, 20):
        draw.ellipse([x - 2, source_y - 2, x + 2, source_y + 2], fill=(25, 45, 75))

    packet_span = (target_x - node_r) - (source_x + node_r)
    for p in range(3):
        u_p = (progress * 1.6 - p * 0.22) % 1.0
        if 0.05 < u_p < 0.95:
            px = source_x + node_r + int(packet_span * u_p)
            py = source_y
            draw.rounded_rectangle([px - 18, py - 12, px + 18, py + 12], radius=6, fill=GOLD_ACCENT)
            draw.text((px - 10, py - 8), "01", fill=(0, 0, 0), font=_load_font(14, bold=True))

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag)
    return img


def _render_frame_universal_data_viz(
    frame_idx: int,
    total_frames: int,
    title: str = "Data Visualization",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Data Visualization (Type I).
    Visualizes accelerating growth curve, metrics, numbers, or exponential expansion.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=1010)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.DATA_VIZ)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Growth Metrics").strip()
    tag = str(meta.get("supporting_text") or "EXPONENTIAL GROWTH").strip()
    claim = str(meta.get("core_claim") or narration or f"Accelerating rapidly over time").strip()

    hud_bb = _draw_hud_badge(draw, "Data & Metrics", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    gx0 = GRID_MARGIN_X + 24
    gx1 = WIDTH - GRID_MARGIN_X - 24
    gy_bottom = vis_bb.cy + 160
    gy_top = vis_bb.y0 + 60
    gw = gx1 - gx0
    gh = gy_bottom - gy_top

    # Graph backdrop
    _draw_subject_backdrop(draw, BoundingBox(gx0 - 10, gy_top - 10, gx1 + 10, gy_bottom + 120))

    draw.line([(gx0, gy_top), (gx0, gy_bottom), (gx1, gy_bottom)], fill=CYAN_ACCENT, width=3)
    for step in range(1, 5):
        y_line = gy_bottom - int(gh * step / 4.0)
        draw.line([(gx0, y_line), (gx1, y_line)], fill=(20, 32, 56), width=1)

    curve_pts: List[Tuple[int, int]] = []
    max_steps = int(gw * progress)
    for x_offset in range(0, max_steps + 1, 6):
        u = x_offset / float(gw)
        y_val = gy_bottom - int(gh * (u ** 2.2))
        curve_pts.append((gx0 + x_offset, y_val))

    if len(curve_pts) > 1:
        draw.line(curve_pts, fill=CYAN_ACCENT, width=6)
        draw.line(curve_pts, fill=WHITE, width=2)
        lead_x, lead_y = curve_pts[-1]
        draw.ellipse([lead_x - 12, lead_y - 12, lead_x + 12, lead_y + 12], fill=GOLD_ACCENT, outline=WHITE, width=2)

    val_int = int(100 + (progress ** 2.2) * 9400)
    font_val = _load_font(42, bold=True)
    font_lbl = _load_font(20, bold=False)

    badge_y = gy_bottom + 25
    draw.rounded_rectangle([gx0, badge_y, gx1, badge_y + 85], radius=14, fill=(10, 16, 32), outline=GOLD_ACCENT, width=2)
    draw.text((gx0 + 25, badge_y + 16), f"+{val_int:,} units", fill=GOLD_ACCENT, font=font_val)
    draw.text((gx0 + 25, badge_y + 60), "COMPOUND VELOCITY INDEX", fill=MUTED_TEXT, font=font_lbl)

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag)
    return img


def _render_frame_universal_map_timeline(
    frame_idx: int,
    total_frames: int,
    title: str = "Timeline & History",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Map/Timeline (Type J).
    Visualizes chronology, historical progression, evolution, or milestones over time.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=1212)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.MAP_TIMELINE)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Timeline").strip()
    tag = str(meta.get("supporting_text") or "CHRONOLOGICAL PROGRESSION").strip()
    claim = str(meta.get("core_claim") or narration or f"Progression over time").strip()

    hud_bb = _draw_hud_badge(draw, "Chronological Evolution", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    milestones = [
        ("PHASE 01 — INCEPTION", "Foundational baseline established"),
        ("PHASE 02 — ACCELERATION", "Rapid expansion across systems"),
        ("PHASE 03 — MODERN STATE", "Current mature architecture"),
    ]

    track_x = GRID_MARGIN_X + 48
    top_y = vis_bb.y0 + 50
    bottom_y = vis_bb.y1 - 60

    draw.line([(track_x, top_y), (track_x, bottom_y)], fill=(30, 48, 80), width=4)
    active_y = top_y + int((bottom_y - top_y) * progress)
    draw.line([(track_x, top_y), (track_x, active_y)], fill=CYAN_ACCENT, width=6)

    font_m_hd = _load_font(24, bold=True)
    font_m_sub = _load_font(20, bold=False)

    num_m = len(milestones)
    for i, (m_title, m_desc) in enumerate(milestones):
        m_y = top_y + int((bottom_y - top_y) * (i / float(num_m - 1)))
        is_lit = (active_y >= m_y - 10)
        node_col = GOLD_ACCENT if is_lit else (40, 56, 85)

        draw.ellipse([track_x - 16, m_y - 16, track_x + 16, m_y + 16],
                     fill=(10, 16, 32), outline=node_col, width=3)
        if is_lit:
            draw.ellipse([track_x - 6, m_y - 6, track_x + 6, m_y + 6], fill=GOLD_ACCENT)

        card_x0 = track_x + 40
        card_w = WIDTH - GRID_MARGIN_X - card_x0
        draw.rounded_rectangle([card_x0, m_y - 35, card_x0 + card_w, m_y + 45],
                                radius=12, fill=(12, 20, 38) if is_lit else (8, 12, 22),
                                outline=CYAN_ACCENT if is_lit else (30, 42, 65), width=2)
        draw.text((card_x0 + 20, m_y - 25), m_title, fill=WHITE if is_lit else MUTED_TEXT, font=font_m_hd)
        draw.text((card_x0 + 20, m_y + 10), m_desc, fill=CYAN_ACCENT if is_lit else (80, 100, 130), font=font_m_sub)

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag)
    return img


def _render_frame_universal_hero_visual(
    frame_idx: int,
    total_frames: int,
    title: str = "Hero Subject",
    narration: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Universal Hero Visual (Type A).
    Visualizes a dominant central subject with semantic adaptation for optical lenses, sensors, ISP, or physical entities.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    meta = metadata or {}
    bg_family = _resolve_background_family(meta, title, narration)
    _draw_contextual_bg(img, bg_family=bg_family, seed=1313)
    draw = ImageDraw.Draw(img)
    composer = SceneComposer(CompositionType.HERO_VISUAL)

    t = frame_idx / float(max(1, total_frames - 1))
    progress = _ease_in_out(t)

    subject = str(meta.get("visual_subject") or title or "Core Phenomenon").strip()
    tag = str(meta.get("supporting_text") or "PRIMARY SUBJECT").strip()
    claim = str(meta.get("core_claim") or narration or f"Focal observation").strip()

    hud_bb = _draw_hud_badge(draw, "Focal Phenomenon", subject.upper()[:24],
                              detail=claim[:75], y_pos=80, composer=composer)
    vis_bb = composer.reserve_visual()

    cx, cy = vis_bb.cx, vis_bb.cy

    scene_text = f"{subject} {narration} {claim}".lower()
    is_sensor  = bg_family == "microscopic_sensor" or any(w in scene_text for w in ["sensor", "pixel", "bayer", "photodiode", "semiconductor", "silicon"])
    is_isp     = bg_family == "data_computational" or any(w in scene_text for w in ["isp", "processing", "comput", "algorithm", "demosaic", "tone map", "raw data"])
    is_optical = bg_family == "optical_lens" or any(w in scene_text for w in ["lens", "aperture", "optic", "refract", "light ray", "glass", "diaphragm"])

    # 1. Microscopic Bayer Sensor Matrix (prioritize sensor if scene discusses silicon/pixels)
    if is_sensor:
        _draw_subject_backdrop(draw, BoundingBox(cx - 260, cy - 260, cx + 260, cy + 260))

        # Silicon die base
        die_w = 400
        draw.rounded_rectangle([cx - die_w // 2, cy - die_w // 2, cx + die_w // 2, cy + die_w // 2],
                               radius=16, fill=(10, 16, 28), outline=(40, 60, 95), width=2)

        # Bayer pixel array: 4x4 grid (Red, Green, Green, Blue)
        cell_size = 72
        start_x = cx - 2 * cell_size
        start_y = cy - 2 * cell_size
        bayer_colors = [
            [(220, 50, 50), (40, 200, 90), (220, 50, 50), (40, 200, 90)],
            [(40, 200, 90), (50, 120, 240), (40, 200, 90), (50, 120, 240)],
            [(220, 50, 50), (40, 200, 90), (220, 50, 50), (40, 200, 90)],
            [(40, 200, 90), (50, 120, 240), (40, 200, 90), (50, 120, 240)],
        ]
        for row in range(4):
            for col in range(4):
                bx0 = start_x + col * cell_size + 4
                by0 = start_y + row * cell_size + 4
                bx1 = bx0 + cell_size - 8
                by1 = by0 + cell_size - 8
                base_col = bayer_colors[row][col]
                # Modulate brightness with photon accumulation progress
                accum = min(1.0, progress * 1.3)
                c_fill = (int(base_col[0] * accum), int(base_col[1] * accum), int(base_col[2] * accum))
                draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, fill=c_fill, outline=(80, 100, 140), width=1)
                # Microlens curvature reflection
                draw.arc([bx0 + 4, by0 + 4, bx1 - 4, by1 - 4], start=210, end=330, fill=(240, 255, 255), width=2)

        badge_font = _load_font(20, bold=True)
        draw.text((cx - 130, cy + die_w // 2 + 25), "BAYER FILTER CMOS SENSOR", fill=CYAN_ACCENT, font=badge_font)

    # 2. Optical Lens Assembly
    elif is_optical or bg_family == "optical_lens":
        _draw_subject_backdrop(draw, BoundingBox(cx - 260, cy - 260, cx + 260, cy + 260))

        # Outer metallic lens barrel
        for r_bar in [240, 220, 195]:
            draw.ellipse([cx - r_bar, cy - r_bar, cx + r_bar, cy + r_bar], outline=(40, 56, 85), width=2)
        # Precision index markings along barrel
        for angle_deg in range(0, 360, 15):
            rad = math.radians(angle_deg)
            x_in = cx + int(220 * math.cos(rad))
            y_in = cy + int(220 * math.sin(rad))
            x_out = cx + int(235 * math.cos(rad))
            y_out = cy + int(235 * math.sin(rad))
            draw.line([(x_in, y_in), (x_out, y_out)], fill=(60, 85, 120), width=1)

        # 6-blade iris aperture
        ap_r = int(90 + 30 * math.sin(progress * math.pi))
        draw.ellipse([cx - ap_r, cy - ap_r, cx + ap_r, cy + ap_r], fill=(6, 10, 18), outline=CYAN_ACCENT, width=3)
        for b in range(6):
            b_rad = math.radians(b * 60 + progress * 40)
            bx = cx + int(ap_r * math.cos(b_rad))
            by = cy + int(ap_r * math.sin(b_rad))
            draw.line([(bx, by), (cx, cy)], fill=(20, 35, 60), width=2)

        # Refraction curved glass highlights
        draw.arc([cx - 160, cy - 160, cx + 160, cy + 160], start=200, end=320, fill=(0, 210, 255), width=3)
        draw.arc([cx - 120, cy - 120, cx + 120, cy + 120], start=30, end=110, fill=GOLD_ACCENT, width=2)

        # Converging light rays from top/left/right toward center
        ray_progress = (t * 2.0) % 1.0
        for ray_angle in [-60, -30, 0, 30, 60]:
            rad = math.radians(ray_angle - 90)
            ray_x0 = cx + int(380 * math.cos(rad))
            ray_y0 = cy + int(380 * math.sin(rad))
            ray_x1 = cx + int(ap_r * 0.4 * math.cos(rad))
            ray_y1 = cy + int(ap_r * 0.4 * math.sin(rad))
            draw.line([(ray_x0, ray_y0), (ray_x1, ray_y1)], fill=(0, 160, 220), width=2)
            # Traveling photon packet
            px = ray_x0 + int((ray_x1 - ray_x0) * ray_progress)
            py = ray_y0 + int((ray_y1 - ray_y0) * ray_progress)
            draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=GOLD_ACCENT)

        # Lens spec badge
        badge_font = _load_font(20, bold=True)
        draw.text((cx - 110, cy + 180), "24mm f/1.8 WIDE ANGLE", fill=GOLD_ACCENT, font=badge_font)

    # 3. Computational ISP / Neural Pipeline
    elif is_isp or bg_family == "data_computational":
        _draw_subject_backdrop(draw, BoundingBox(cx - 260, cy - 240, cx + 260, cy + 240))

        # Central processor die
        draw.rounded_rectangle([cx - 120, cy - 120, cx + 120, cy + 120], radius=16, fill=(12, 20, 36), outline=CYAN_ACCENT, width=3)
        draw.text((cx - 50, cy - 15), "ISP CORE", fill=WHITE, font=_load_font(24, bold=True))
        draw.text((cx - 65, cy + 20), "30B OPS/SEC", fill=GOLD_ACCENT, font=_load_font(18, bold=False))

        # Input raw bus from left
        draw.line([(vis_bb.x0 + 40, cy), (cx - 120, cy)], fill=CYAN_ACCENT, width=4)
        draw.text((vis_bb.x0 + 45, cy - 35), "RAW MOSAIC", fill=CYAN_ACCENT, font=_load_font(18, bold=True))

        # Output RGB bus to right
        draw.line([(cx + 120, cy), (vis_bb.x1 - 40, cy)], fill=GOLD_ACCENT, width=4)
        draw.text((vis_bb.x1 - 170, cy - 35), "PROCESSED RGB", fill=GOLD_ACCENT, font=_load_font(18, bold=True))

        badge_font = _load_font(20, bold=True)
        draw.text((cx - 125, cy + 160), "IMAGE SIGNAL PROCESSOR", fill=WHITE, font=badge_font)

    # 4. Universal Focal Hero Subject (General fallback)
    else:
        _draw_subject_backdrop(draw, BoundingBox(cx - 240, cy - 240, cx + 240, cy + 240))
        halo_r = 160
        for i in range(3):
            phase = (t * 1.5 + i * 0.33) % 1.0
            r_pulse = int(halo_r + phase * 60)
            draw.ellipse([cx - r_pulse, cy - r_pulse, cx + r_pulse, cy + r_pulse],
                         outline=(0, int(180 * (1 - phase)), int(230 * (1 - phase))), width=2)

        draw.ellipse([cx - 85, cy - 85, cx + 85, cy + 85], fill=(8, 14, 28), outline=CYAN_ACCENT, width=3)
        draw.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], fill=(0, 200, 255), outline=WHITE, width=2)

        ret_len = 110
        draw.line([(cx - ret_len, cy), (cx - 95, cy)], fill=GOLD_ACCENT, width=3)
        draw.line([(cx + 95, cy), (cx + ret_len, cy)], fill=GOLD_ACCENT, width=3)
        draw.line([(cx, cy - ret_len), (cx, cy - 95)], fill=GOLD_ACCENT, width=3)
        draw.line([(cx, cy + 95), (cx, cy + ret_len)], fill=GOLD_ACCENT, width=3)

        font_sub = _load_font(26, bold=True)
        draw.text((cx - 80, cy + 120), subject.upper()[:20], fill=WHITE, font=font_sub)

    cap_text = narration if narration else claim
    _draw_caption_bar(draw, cap_text, composer=composer, tag=tag)
    return img



def _extract_process_steps(title: str, narration: str = "") -> List[str]:
    """Dynamically determine 4 process steps based on video topic."""
    combined = (title + " " + narration).lower()
    if any(w in combined for w in ["wi-fi", "wifi", "network", "radio", "signal", "router", "internet"]):
        return ["Binary Data (0s & 1s)", "Radio Wave Modulation", "Wireless Air Transmission", "Receiver Demodulation"]
    if any(w in combined for w in ["black hole", "gravity", "light", "space", "star", "physics"]):
        return ["Initial Photon Path", "Gravitational Field Interaction", "Curvature & Deflection", "Lensed Observation"]
    return ["Input & Signal Generation", "Transmission & Propagation", "System Processing", "Output & Reception"]


# ─────────────────────────────────────────────────────────────────────────────
# CLIP COMPOSITOR & EXPORTER
# ─────────────────────────────────────────────────────────────────────────────

CONCEPT_RENDERERS: Dict[str, Callable[[int, int], Image.Image]] = {
    "straight_light_ray": _render_frame_straight_ray,
    "normal_path": _render_frame_straight_ray,
    "spacetime_curvature": _render_frame_spacetime_warp,
    "mass_appears": _render_frame_spacetime_warp,
    "light_approaches": _render_frame_light_approaches,
    "approaching_trajectory": _render_frame_light_approaches,
    "light_bending": _render_frame_light_bending,
    "gravitational_deflection": _render_frame_light_bending,
    "einstein_ring": _render_frame_einstein_ring,
    "gravitational_lensing": _render_frame_einstein_ring,
    "scale_comparison": _render_frame_scale_comparison,
    "cosmic_scale": _render_frame_scale_comparison,
    "comparison": _render_frame_comparison,
    "before_after": _render_frame_comparison,
    "data_metric": _render_frame_data_metric,
    "data_visualization": _render_frame_data_metric,
    "text_emphasis": _render_frame_text_emphasis,
    "conceptual_payoff": _render_frame_text_emphasis,
    "radio_waves": _render_frame_radio_waves,
    "wireless_signal": _render_frame_radio_waves,
    "binary_packets": _render_frame_binary_packets,
    "data_packets": _render_frame_binary_packets,
    "frequency_spectrum": _render_frame_frequency_spectrum,
    "frequency_comparison": _render_frame_frequency_spectrum,
    "process_visualization": _render_frame_process_diagram,
    "process_steps": _render_frame_process_diagram,
    # Universal Archetypes (A through L)
    "hero_visual": _render_frame_universal_hero_visual,
    "physical_demo": _render_frame_universal_physical_demo,
    "transformation": _render_frame_universal_transformation,
    "object_interaction": _render_frame_universal_object_interaction,
    "data_viz": _render_frame_universal_data_viz,
    "map_timeline": _render_frame_universal_map_timeline,
}


def validate_visual_semantic_fit(concept_key: str, scene: Dict[str, Any]) -> str:
    """Validate that the visual representation matches the core claim of the narration.
    Rejects generic flowchart if narration describes physical movement, force, or transformation."""
    combined = " ".join([
        str(scene.get("narration") or ""),
        str(scene.get("visual_action") or ""),
        str(scene.get("core_claim") or ""),
    ]).lower()

    if concept_key in ("process_visualization", "process_steps"):
        # Re-route if physical action or transformation is described
        if any(w in combined for w in ["thrust", "gravity", "push", "pull", "lift", "fall", "engine", "move", "speed", "propel"]):
            logger.info("Semantic Validator: Re-routed flowchart to physical_demo based on physical action")
            return "physical_demo"
        if any(w in combined for w in ["melt", "heat", "freeze", "burn", "cook", "morph", "transform"]):
            logger.info("Semantic Validator: Re-routed flowchart to transformation based on state change")
            return "transformation"
        if any(w in combined for w in ["packet", "radio", "signal", "router", "phone", "transmit", "receive", "broadcast"]):
            logger.info("Semantic Validator: Re-routed flowchart to object_interaction based on communication")
            return "object_interaction"
        if any(w in combined for w in ["growth", "interest", "balance", "metric", "rate", "scale", "multiply"]):
            logger.info("Semantic Validator: Re-routed flowchart to data_viz based on metrics")
            return "data_viz"

    return concept_key


def detect_concept_key(scene: Dict[str, Any], topic: str = "") -> Optional[str]:
    """Detect visual archetype semantically based on scene meaning."""
    v_type = (scene.get("visual_type") or "").strip().lower()

    # Photographic types should NOT use procedural motion graphics
    if v_type in ("cinematic_photo", "establishing_shot"):
        return None

    # 1. Explicit concept_key in scene metadata
    ck = (scene.get("concept_key") or "").strip().lower()
    if ck and ck in CONCEPT_RENDERERS:
        return validate_visual_semantic_fit(ck, scene)

    # 2. Semantic mapping from composition archetype
    comp = str(scene.get("composition") or "").strip().upper()
    if "PHYSICAL" in comp or comp == "B":
        return "physical_demo"
    if "TRANSFORMATION" in comp or comp == "D":
        return "transformation"
    if "OBJECT_INTERACTION" in comp or comp == "K":
        return "object_interaction"
    if "DATA" in comp or comp == "I":
        return "data_viz"
    if "TIMELINE" in comp or "MAP" in comp or comp == "J":
        return "map_timeline"
    if "HERO" in comp or comp == "A" or "CLOSE" in comp or comp == "F":
        return "hero_visual"
    if "COMPARISON" in comp or comp == "E":
        return "comparison"
    if ("PROCESS" in comp or comp == "C") and any(w in (str(scene.get("narration") or "")).lower() for w in ["step", "stage", "phase", "workflow"]):
        return "process_visualization"

    # 3. Semantic keyword analysis of narration + visual action + core claim
    fields = [
        str(scene.get("visual_action") or ""),
        str(scene.get("visual_subject") or ""),
        str(scene.get("narration") or ""),
        str(scene.get("core_claim") or ""),
        str(scene.get("visual_description") or ""),
    ]
    combined = " ".join(fields).lower()

    # Data growth & quantitative acceleration (compound interest, balance, metrics, graphs)
    if any(k in combined for k in ["balance", "interest", "compound", "revenue", "metric", "graph", "chart", "multiply", "exponential", "growth"]):
        return "data_viz"

    # Transformation & phase change (melting, heating, morphing)
    if any(k in combined for k in ["melt", "melting", "heat", "cool", "freeze", "transform", "morph", "convert", "state change"]):
        return "transformation"

    # Object interaction & networking (packets, signals, communication)
    if any(k in combined for k in ["packet", "radio wave", "antenna", "signal", "wireless", "router", "phone", "transmit", "receive", "broadcast"]):
        return "object_interaction"

    # Physical dynamics (thrust, gravity, lift, motion, falling)
    if any(k in combined for k in ["thrust", "gravity", "pull", "push", "lift", "fall", "propel", "drag", "force", "downward", "upward"]):
        return "physical_demo"
    if "accelerat" in combined and any(w in combined for w in ["engine", "craft", "plane", "mass", "vehicle", "speed", "velocity"]):
        return "physical_demo"

    # Timeline & chronology
    if any(k in combined for k in ["timeline", "history", "years", "decades", "centuries", "chronolog"]):
        return "map_timeline"

    # Physics / astronomy specific keys
    if any(k in combined for k in ["straight", "normal path", "euclidean", "flat space", "uncurved"]):
        return "straight_light_ray"
    if any(k in combined for k in ["mass appears", "spacetime grid", "warping", "fabric of space", "gravity well"]):
        return "spacetime_curvature"
    if any(k in combined for k in ["approaches", "approaching", "nearing", "enters gravitational"]):
        return "light_approaches"
    if any(k in combined for k in ["bend", "bending", "curves", "curved path", "deflect", "trajectory"]):
        return "light_bending"
    if any(k in combined for k in ["einstein ring", "ring forms", "halo", "gravitational lens", "lensing"]):
        return "einstein_ring"
    if any(k in combined for k in ["scale", "light years", "cosmic scale", "pull back", "kilometers", "proportions"]):
        return "scale_comparison"
    if any(k in combined for k in ["compare", "versus", "before and after", "newton vs", "difference"]):
        return "comparison"

    # Default fallback: Hero Visual or Physical Demo (NEVER a generic flowchart!)
    if v_type in ("animated_diagram", "conceptual_animation", "scientific_diagram"):
        return "hero_visual"

    return "hero_visual"


def render_motion_graphic_clip(
    concept_key: str,
    output_mp4_path: str,
    duration_seconds: float = 4.0,
    title: str = "Science Explainer",
    narration: str = "",
    scene_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Render a standalone 1080x1920 (9:16) MP4 motion graphics animation clip.
    
    Args:
        concept_key: One of the recognized concept keys (straight_light_ray, physical_demo, etc.)
        output_mp4_path: Filepath where the final MP4 will be saved.
        duration_seconds: Duration in seconds for the clip (typically 3 to 6 seconds).
        title: Title string for badges/headers.
        narration: Optional narration string for context-aware diagrams.
        scene_metadata: Optional dictionary with V3 visual intent metadata.

    Returns:
        True if successfully rendered, False otherwise.
    """
    try:
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        total_frames = max(30, int(round(duration_seconds * FPS)))

        meta = scene_metadata or {}
        ck_clean = concept_key.lower().strip()
        ck_clean = validate_visual_semantic_fit(ck_clean, meta)

        # Dispatch based on concept key
        if ck_clean in ("physical_demo", "thrust", "gravity", "lift", "force"):
            renderer = lambda f, tot: _render_frame_universal_physical_demo(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("transformation", "morph", "state_change", "phase_change"):
            renderer = lambda f, tot: _render_frame_universal_transformation(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("object_interaction", "signal_exchange", "packet_transfer"):
            renderer = lambda f, tot: _render_frame_universal_object_interaction(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("data_viz", "growth", "metrics", "chart"):
            renderer = lambda f, tot: _render_frame_universal_data_viz(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("map_timeline", "timeline", "chronology"):
            renderer = lambda f, tot: _render_frame_universal_map_timeline(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("hero_visual", "hero_focus", "core_concept"):
            renderer = lambda f, tot: _render_frame_universal_hero_visual(f, tot, title=title, narration=narration, metadata=meta)
        elif ck_clean in ("process_visualization", "process_steps"):
            steps = _extract_process_steps(title, narration)
            renderer = lambda f, tot: _render_frame_process_diagram(f, tot, title=title, steps=steps)
        else:
            base_renderer = CONCEPT_RENDERERS.get(ck_clean)
            if base_renderer:
                renderer = base_renderer
            else:
                renderer = lambda f, tot: _render_frame_universal_hero_visual(f, tot, title=title, narration=narration, metadata=meta)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            output_mp4_path,
        ]

        logger.info(f"Rendering motion graphic clip for concept '{concept_key}' -> '{ck_clean}' ({total_frames} frames) -> {output_mp4_path}")
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        for f_idx in range(total_frames):
            frame_img = renderer(f_idx, total_frames)
            proc.stdin.write(frame_img.tobytes())

        proc.stdin.close()
        proc.wait(timeout=60)

        if proc.returncode == 0 and os.path.isfile(output_mp4_path) and os.path.getsize(output_mp4_path) > 1000:
            logger.info(f"Successfully rendered motion graphic clip: {output_mp4_path} ({os.path.getsize(output_mp4_path)} bytes)")
            return True
        else:
            logger.error(f"FFmpeg failed with returncode {proc.returncode}")
            return False

    except Exception as e:
        logger.exception(f"Error rendering motion graphic clip for concept '{concept_key}': {e}")
        return False
