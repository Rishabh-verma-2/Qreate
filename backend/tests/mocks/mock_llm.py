"""Mock Qwen3 LLM client for unit and integration tests."""

import json
from typing import Any, Dict, List, Optional

SAMPLE_VIDEO_PLAN_DICT: Dict[str, Any] = {
    "title": "Cosmic Voyage: Into the Black Hole",
    "total_duration": 15,
    "style": "cinematic 3D animation",
    "aspect_ratio": "16:9",
    "fps": 24,
    "language": "en",
    "characters": [
        {
            "id": "char_01",
            "name": "Captain Vance",
            "description": "A seasoned astronaut in a sleek obsidian space suit.",
            "appearance": "White short hair, cybernetic eye, weathered face",
            "clothing": "Obsidian EVA pressure suit with glowing blue accents",
            "style": "cinematic realistic",
            "reference_image": None,
        }
    ],
    "scenes": [
        {
            "id": "scene_001",
            "duration": 5,
            "narration": "Beyond the event horizon, physics as we understand it dissolves.",
            "visual_prompt": "Captain Vance looking out the spaceship observation deck towards an accretion disk, glowing plasma rings, stars bending around black hole.",
            "motion_prompt": "Slow dolly-in towards Vance as the glowing light reflects across his helmet visor.",
            "camera": {
                "shot_type": "medium close-up",
                "movement": "dolly-in",
                "angle": "eye-level",
            },
            "style": "cinematic 3D animation",
            "characters": ["char_01"],
            "transition_in": "fade",
            "transition_out": "cut",
            "reference_image": None,
        },
        {
            "id": "scene_002",
            "duration": 5,
            "narration": "Gravitational tides stretch starlight into infinite spiraling ribbons.",
            "visual_prompt": "Vast swirling accretion disk of a supermassive black hole with relativistic jets erupting into deep space.",
            "motion_prompt": "Camera orbits the spinning singularity as luminous matter accelerates inward.",
            "camera": {
                "shot_type": "wide",
                "movement": "orbit",
                "angle": "high-angle",
            },
            "style": "cinematic 3D animation",
            "characters": [],
            "transition_in": "cut",
            "transition_out": "cut",
            "reference_image": None,
        },
        {
            "id": "scene_003",
            "duration": 5,
            "narration": "A journey from which no light ever returns.",
            "visual_prompt": "The spaceship engines firing blue ion thrusters, diving towards the photon sphere.",
            "motion_prompt": "Fast tracking shot behind the starship as it accelerates into the void.",
            "camera": {
                "shot_type": "aerial",
                "movement": "pan-left",
                "angle": "low-angle",
            },
            "style": "cinematic 3D animation",
            "characters": [],
            "transition_in": "cut",
            "transition_out": "fade",
            "reference_image": None,
        },
    ],
}


class MockQwenClient:
    """Mock implementation of QwenClient for testing."""

    def __init__(self, plan_data: Optional[Dict[str, Any]] = None, fail_first: bool = False):
        self.plan_data = plan_data or SAMPLE_VIDEO_PLAN_DICT
        self.call_count = 0
        self.fail_first = fail_first

    async def ping(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        self.call_count += 1
        if self.fail_first and self.call_count == 1:
            return "Invalid JSON output { not closed"
        return json.dumps(self.plan_data)

    async def chat_with_retry(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return await self.chat(messages, **kwargs)
