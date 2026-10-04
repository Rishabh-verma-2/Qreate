"""Voice catalog + audio previews for the creator's voice picker."""

import os
import tempfile
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.media import voices
from app.services.media.tts import synthesize

router = APIRouter(prefix="/api/voices", tags=["Voices"])

_previews: Dict[str, bytes] = {}  # voice_id|language → mp3 bytes (small, cached for the process)


@router.get("", response_model=dict)
async def list_voices():
    return {"data": voices.catalog()}


@router.get("/preview")
async def preview_voice(voice_id: str, language: Optional[str] = None):
    if not voices.is_valid_voice(voice_id):
        raise HTTPException(status_code=404, detail="Unknown voice")
    lang = language if language in voices.CATALOG else voices.language_of(voice_id) or "English"
    key = f"{voice_id}|{lang}"
    if key not in _previews:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "preview.mp3")
            await synthesize(voices.sample_text(lang), path, voice_id, rate="+4%")
            with open(path, "rb") as f:
                _previews[key] = f.read()
    return Response(
        content=_previews[key],
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
