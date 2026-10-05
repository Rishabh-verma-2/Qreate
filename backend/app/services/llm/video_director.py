"""AI Video Director — converts a user prompt into a validated VideoPlan.

Pipeline:
  1. Try Qwen3 (local vLLM) → fastest, most capable for structured output
  2. Fall back to cloud LLM chain (groq → openrouter → gemini → ...) if Qwen unavailable
  3. Parse and validate JSON → VideoPlan
  4. If validation fails: feed error back to LLM and retry once
  5. If still failing: raise VideoPlanError

This module is the "brain" of the AI Director system.
"""

import json
import logging
from typing import Optional

from pydantic import ValidationError

from app.core.errors import VideoPlanError, QwenUnavailableError
from app.services.llm.client import extract_json, generate_json
from app.services.llm.prompts import (
    VIDEO_DIRECTOR_SYSTEM_PROMPT,
    build_user_prompt,
    build_correction_prompt,
    build_scene_regen_prompt,
)
from app.services.llm.qwen_client import get_qwen_client
from app.services.llm.schemas import Scene, VideoPlan, validate_video_plan

logger = logging.getLogger(__name__)


class QwenVideoDirector:
    """Orchestrates the AI Video Director workflow.

    Tries Qwen3 (local) first, falls back to cloud LLM chain if unavailable.
    All output is validated against the VideoPlan Pydantic schema.

    Usage::

        director = QwenVideoDirector()
        plan = await director.plan(
            prompt="Create a 30 second video about black holes",
            style="cinematic 3D animation",
            duration=30,
            aspect_ratio="16:9",
        )
    """

    async def plan(
        self,
        prompt: str,
        style: str = "cinematic",
        duration: int = 30,
        aspect_ratio: str = "16:9",
        language: str = "en",
    ) -> VideoPlan:
        """Generate a structured VideoPlan from a user prompt.

        Args:
            prompt: The user's video request in natural language.
            style: Visual style descriptor passed to the LLM.
            duration: Target total duration in seconds.
            aspect_ratio: "16:9" or "9:16".
            language: ISO 639-1 language code.

        Returns:
            A validated VideoPlan ready for the generation pipeline.

        Raises:
            VideoPlanError: If no LLM can produce a valid plan after retries.
        """
        user_msg = build_user_prompt(prompt, style, duration, aspect_ratio, language)
        messages = [
            {"role": "system", "content": VIDEO_DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        # ── 1. Try local Qwen3 first ─────────────────────────────────────────
        qwen = get_qwen_client()
        if await qwen.ping():
            logger.info("Qwen3 available — using local vLLM for video planning")
            plan = await self._plan_with_qwen(qwen, messages, user_msg, duration)
            if plan is not None:
                return plan
            logger.warning("Qwen3 failed to produce a valid plan — falling back to cloud LLMs")
        else:
            logger.info("Qwen3 not available — using cloud LLM fallback for video planning")

        # ── 2. Fall back to cloud LLM chain ──────────────────────────────────
        return await self._plan_with_cloud(messages, user_msg, duration)

    async def _plan_with_qwen(
        self,
        qwen,
        messages: list,
        user_msg: str,
        duration: int,
    ) -> Optional[VideoPlan]:
        """Attempt planning with Qwen3; return None if it fails after retries."""
        for attempt in range(2):
            try:
                raw = await qwen.chat_with_retry(messages, max_attempts=2, temperature=0.7)
                obj = extract_json(raw)
                plan = validate_video_plan(obj)
                logger.info(
                    f"Qwen3 video plan: '{plan.title}', {len(plan.scenes)} scenes, "
                    f"{sum(s.duration for s in plan.scenes)}s total"
                )
                return plan
            except QwenUnavailableError:
                return None
            except (ValueError, json.JSONDecodeError, ValidationError) as e:
                if attempt == 0:
                    # First failure: send correction prompt
                    logger.warning(f"Qwen3 plan attempt 1 invalid ({e}). Sending correction.")
                    correction = build_correction_prompt(str(e)[:300], user_msg)
                    messages = list(messages) + [
                        {"role": "assistant", "content": raw if "raw" in dir() else ""},
                        {"role": "user", "content": correction},
                    ]
                else:
                    logger.warning(f"Qwen3 plan attempt 2 also invalid ({e}). Giving up on Qwen3.")
                    return None
            except Exception as e:
                logger.warning(f"Qwen3 unexpected error (attempt {attempt + 1}): {e}")
                if attempt >= 1:
                    return None
        return None

    async def _plan_with_cloud(self, messages: list, user_msg: str, duration: int) -> VideoPlan:
        """Plan using the existing cloud LLM provider chain as fallback."""

        def _validate(obj: dict) -> dict:
            """Used as the generate_json validate callback."""
            plan = validate_video_plan(obj)
            return plan.model_dump()

        try:
            result = await generate_json(
                messages,
                validate=_validate,
                temperature=0.7,
                max_tokens=4096,
            )
            # result is the dumped dict — re-parse into model
            return validate_video_plan(result)
        except Exception as e:
            raise VideoPlanError(
                f"All LLM providers (Qwen3 + cloud fallbacks) failed to produce a valid video plan. "
                f"Last error: {str(e)[:300]}"
            )

    async def regenerate_scene(
        self,
        original_scene: dict,
        instruction: str,
        video_style: str,
    ) -> Scene:
        """Regenerate a single scene based on a user instruction.

        The LLM receives the original scene JSON + the instruction and returns
        an updated scene with modified visual/motion prompts.

        Returns:
            Updated Scene Pydantic model.

        Raises:
            VideoPlanError: If the LLM cannot produce a valid updated scene.
        """
        prompt = build_scene_regen_prompt(original_scene, instruction, video_style)
        messages = [
            {"role": "system", "content": VIDEO_DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        qwen = get_qwen_client()
        raw = None

        if await qwen.ping():
            try:
                raw = await qwen.chat_with_retry(messages, max_attempts=2)
            except Exception as e:
                logger.warning(f"Qwen3 scene regen failed: {e}. Trying cloud LLMs.")

        if raw is None:
            try:
                raw = await generate_json(messages, temperature=0.7, max_tokens=1024)
                raw = json.dumps(raw)
            except Exception as e:
                raise VideoPlanError(f"Scene regeneration failed: {e}")

        try:
            obj = extract_json(raw) if isinstance(raw, str) else raw
            # Preserve fields not in the LLM output (id, reference_image)
            merged = {**original_scene, **obj}
            return Scene.model_validate(merged)
        except (ValueError, json.JSONDecodeError, ValidationError) as e:
            raise VideoPlanError(f"Scene JSON validation failed after regeneration: {e}")
