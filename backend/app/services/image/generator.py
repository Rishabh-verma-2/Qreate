"""Image generation abstraction.

ImageGenerator is the abstract interface. Concrete implementations:
- PillowImageGenerator: no API, generates styled text cards (always available)

The purpose is to produce reference images for characters so that the same
visual appearance is maintained across multiple scenes in I2V mode.
"""

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class ImageGenerator(ABC):
    """Abstract image generator interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        style: str = "",
        width: int = 512,
        height: int = 512,
        output_path: str = "",
    ) -> str:
        """Generate an image and return its local path."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this generator is ready to use."""
        ...


class PillowImageGenerator(ImageGenerator):
    """Generates character reference images using Pillow (no API or GPU needed).

    Creates a styled portrait card with the character description text.
    This is a placeholder that works without a GPU — replace with a real
    image generation service for production character images.
    """

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        style: str = "",
        width: int = 512,
        height: int = 512,
        output_path: str = "",
    ) -> str:
        """Generate a styled character reference card."""
        if not output_path:
            tmp = tempfile.mkdtemp(prefix="char_ref_")
            output_path = os.path.join(tmp, "character.jpg")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
            import random

            # Deterministic color from prompt hash
            rng = random.Random(hash(prompt) % 2 ** 32)
            hue = rng.randint(0, 360)

            # Convert HSV-ish to RGB
            def hsl_to_rgb(h, s=0.6, l=0.35):
                import colorsys
                r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
                return int(r * 255), int(g * 255), int(b * 255)

            bg_color = hsl_to_rgb(hue)
            fg_color = (255, 255, 255)

            img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)

            # Draw character silhouette placeholder
            cx, cy = width // 2, height // 2
            # Head
            draw.ellipse([cx - 60, cy - 150, cx + 60, cy - 30], fill=hsl_to_rgb(hue, 0.4, 0.6))
            # Body
            draw.rectangle([cx - 70, cy - 30, cx + 70, cy + 150], fill=hsl_to_rgb(hue, 0.3, 0.5))

            # Character name / description overlay
            lines = []
            words = prompt.split()
            line = ""
            for word in words[:20]:  # show first 20 words
                if len(line) + len(word) + 1 <= 25:
                    line = f"{line} {word}".strip()
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            lines = lines[:4]  # max 4 lines

            try:
                assets_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                    "assets", "fonts"
                )
                font = ImageFont.truetype(
                    os.path.join(assets_dir, "Poppins-ExtraBold.ttf"), 20
                )
            except Exception:
                font = ImageFont.load_default()

            y_text = cy + 160
            for line in lines:
                w_text = draw.textlength(line, font=font) if hasattr(draw, "textlength") else len(line) * 10
                draw.text(((width - w_text) / 2, y_text), line, fill=fg_color, font=font)
                y_text += 26

            # Slight blur for "photo" feel
            img = img.filter(ImageFilter.GaussianBlur(0.5))
            img.save(output_path, "JPEG", quality=90)
            logger.info(f"PillowImageGenerator: character ref saved at {output_path}")
            return output_path

        except Exception as e:
            logger.warning(f"PillowImageGenerator failed ({e}), creating minimal placeholder")
            # Absolute minimal fallback
            try:
                from PIL import Image
                img = Image.new("RGB", (width, height), (80, 80, 120))
                img.save(output_path, "JPEG", quality=80)
                return output_path
            except Exception:
                raise RuntimeError(f"Cannot generate reference image: {e}")


def get_image_generator() -> ImageGenerator:
    """Return the best available image generator."""
    return PillowImageGenerator()
