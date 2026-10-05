"""Character reference image service.

Ensures each character in a VideoPlan has a stable reference image.
The same image is reused for every scene the character appears in,
which is what enables I2V character consistency in Wan2.1.

Key behaviours:
- If a character already has a reference_image URL/path, use that.
- Otherwise, generate a reference image from appearance + clothing description.
- Cache generated images in the database and on disk for the job.
- Return the local file path so WanVideoEngine can pass it to ComfyUI.
"""

import logging
import os
import tempfile
from typing import Dict, Optional

from app.services.image.generator import get_image_generator
from app.services.llm.schemas import Character, VideoPlan

logger = logging.getLogger(__name__)


class CharacterService:
    """Manages character reference images for a single video generation job.

    Usage::

        service = CharacterService(job_id="abc123", work_dir="/tmp/job_abc123")
        await service.resolve_all(video_plan)
        # Now video_plan.characters each have reference_image set to a local path
    """

    def __init__(self, job_id: str, work_dir: str):
        self.job_id = job_id
        self.work_dir = work_dir
        self._cache: Dict[str, str] = {}  # character_id → local image path
        self._generator = get_image_generator()

    async def resolve_all(self, plan: VideoPlan) -> None:
        """Resolve reference images for all characters in the plan.

        Modifies the plan in-place: sets character.reference_image to a local path.
        Also sets scene.reference_image for the first character in each scene.
        """
        if not plan.characters:
            return

        char_dir = os.path.join(self.work_dir, "characters")
        os.makedirs(char_dir, exist_ok=True)

        for character in plan.characters:
            path = await self.ensure_reference(character, char_dir)
            character.reference_image = path

        # Attach reference image to each scene (uses first character's image for I2V)
        char_map = {c.id: c for c in plan.characters}
        for scene in plan.scenes:
            if scene.characters:
                first_char = char_map.get(scene.characters[0])
                if first_char and first_char.reference_image:
                    scene.reference_image = first_char.reference_image

    async def ensure_reference(self, character: Character, char_dir: str) -> str:
        """Return local path to the character's reference image.

        Creates the image if it doesn't exist yet, using cached result if available.
        """
        # Check in-memory cache first
        if character.id in self._cache:
            return self._cache[character.id]

        # If the plan already has a URL (user-provided or from a previous run), download it
        if character.reference_image and character.reference_image.startswith("http"):
            local_path = await self._download_reference(
                character.reference_image, character.id, char_dir
            )
            self._cache[character.id] = local_path
            return local_path

        # Generate a new reference image
        output_path = os.path.join(char_dir, f"{character.id}.jpg")
        prompt = self._build_gen_prompt(character)

        try:
            path = await self._generator.generate(
                prompt=prompt,
                style=character.style,
                width=512,
                height=512,
                output_path=output_path,
            )
            self._cache[character.id] = path
            logger.info(f"CharacterService: reference image for '{character.name}' → {path}")
            return path
        except Exception as e:
            logger.warning(
                f"CharacterService: failed to generate reference for '{character.name}': {e}. "
                "Scene will use T2V instead of I2V."
            )
            return ""

    def _build_gen_prompt(self, character: Character) -> str:
        """Build a prompt for generating the character's reference image."""
        parts = [
            character.appearance,
            f"wearing {character.clothing}" if character.clothing else "",
            character.style,
            "portrait, full body, clear background, reference sheet",
        ]
        return ", ".join(p for p in parts if p)

    async def _download_reference(self, url: str, char_id: str, dest_dir: str) -> str:
        """Download a character reference image from a URL."""
        import httpx
        dest = os.path.join(dest_dir, f"{char_id}_ref.jpg")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                with open(dest, "wb") as f:
                    f.write(resp.content)
                logger.info(f"CharacterService: downloaded reference for {char_id} from {url}")
                return dest
        except Exception as e:
            logger.warning(f"CharacterService: could not download reference from {url}: {e}")
        return ""

    def get_reference(self, character_id: str) -> Optional[str]:
        """Return cached reference path for a character_id, or None."""
        return self._cache.get(character_id)
