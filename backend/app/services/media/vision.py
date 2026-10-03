"""Visual relevance with CLIP (open-source, runs on CPU; uses CUDA if available).

Stock-site tags describe a clip loosely ("wedding, celebration, beauty"), so tag
matching picks a lipstick close-up for "bride's emotional goodbye". CLIP looks at
each candidate's thumbnail and scores how well the *image* matches the scene's
visual description, so the best-looking match wins.

Optional: if torch/open_clip are not installed or VISUAL_RERANK=false, callers fall
back to tag-based ranking.
"""

import asyncio
import logging
import threading
from functools import lru_cache
from typing import List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_unavailable = False


def _load():
    global _model, _unavailable
    if _model is not None or _unavailable:
        return _model
    with _lock:
        if _model is not None or _unavailable:
            return _model
        try:
            import open_clip
            import torch

            s = get_settings()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(s.CLIP_MODEL, pretrained=s.CLIP_PRETRAINED, device=device)
            model.eval()
            tokenizer = open_clip.get_tokenizer(s.CLIP_MODEL)
            torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
            _model = (model, preprocess, tokenizer, device, torch)
            logger.info(f"CLIP loaded: {s.CLIP_MODEL}/{s.CLIP_PRETRAINED} on {device}")
        except Exception as e:
            _unavailable = True
            logger.warning(f"CLIP unavailable ({e}); using tag-based ranking")
    return _model


def available() -> bool:
    return get_settings().VISUAL_RERANK and _load() is not None


@lru_cache(maxsize=512)
def _text_embedding(text: str):
    model, _, tokenizer, device, torch = _model
    with torch.no_grad():
        emb = model.encode_text(tokenizer([text]).to(device))
        return emb / emb.norm(dim=-1, keepdim=True)


def _score_sync(text: str, image_paths: List[Optional[str]]) -> List[float]:
    from PIL import Image

    model, preprocess, _, device, torch = _model
    scores = [0.0] * len(image_paths)
    tensors, idx = [], []
    for i, p in enumerate(image_paths):
        if not p:
            continue
        try:
            with Image.open(p) as im:
                tensors.append(preprocess(im.convert("RGB")))
                idx.append(i)
        except Exception:
            continue
    if not tensors:
        return scores
    with _lock, torch.no_grad():
        t = _text_embedding(f"a photo of {text}")
        img = model.encode_image(torch.stack(tensors).to(device))
        img = img / img.norm(dim=-1, keepdim=True)
        sims = (img @ t.T).squeeze(1).tolist()
    for i, s in zip(idx, sims):
        scores[i] = float(s)
    return scores


async def score_images(text: str, image_paths: List[Optional[str]]) -> List[float]:
    """Cosine similarity of each image to `text` (0.0 for unreadable images)."""
    if not available():
        return [0.0] * len(image_paths)
    return await asyncio.to_thread(_score_sync, text, image_paths)


async def warm_up() -> None:
    """Load the model in the background at startup so the first job isn't slow."""
    if get_settings().VISUAL_RERANK:
        await asyncio.to_thread(_load)
