"""Provider-agnostic LLM client.

Every provider speaks the OpenAI chat-completions format, so one code path serves
Groq, OpenRouter, Gemini, Agnes and self-hosted Ollama. Providers are tried in
LLM_PROVIDER_ORDER; a failure (network, rate limit, bad JSON) moves on to the next
one, so a single free-tier quota running out never stops the pipeline.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import QreateError

logger = logging.getLogger(__name__)


class LLMError(QreateError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str
    json_mode: bool = True


def _configured_providers() -> List[Provider]:
    s = get_settings()
    catalog = {
        "groq": Provider("groq", "https://api.groq.com/openai/v1", s.GROQ_API_KEY, s.GROQ_MODEL),
        "openrouter": Provider("openrouter", "https://openrouter.ai/api/v1", s.OPENROUTER_API_KEY, s.OPENROUTER_MODEL, json_mode=False),
        "gemini": Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", s.GEMINI_API_KEY, s.GEMINI_MODEL),
        "agnes": Provider("agnes", f"{s.AGNES_BASE_URL.rstrip('/')}/v1", s.AGNES_API_KEY, s.AGNES_CHAT_MODEL, json_mode=False),
        "ollama": Provider("ollama", f"{s.OLLAMA_BASE_URL.rstrip('/')}/v1", "ollama", s.OLLAMA_MODEL),
    }
    providers = []
    for name in [n.strip().lower() for n in s.LLM_PROVIDER_ORDER.split(",") if n.strip()]:
        p = catalog.get(name)
        if not p:
            continue
        if name == "ollama" and not s.OLLAMA_BASE_URL:
            continue
        if name != "ollama" and not p.api_key:
            continue
        providers.append(p)
    return providers


def configured_provider_names() -> List[str]:
    return [p.name for p in _configured_providers()]


def extract_json(raw: str) -> Dict[str, Any]:
    """Parse a JSON object out of an LLM reply, tolerating code fences and chatter."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    candidate = match.group()
    # Trailing commas are the most common small-model mistake
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    return json.loads(candidate)


async def _call(provider: Provider, messages: list, temperature: float, max_tokens: int) -> str:
    payload: Dict[str, Any] = {
        "model": provider.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if provider.json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
    timeout = get_settings().LLM_TIMEOUT_SECONDS
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{provider.base_url}/chat/completions", json=payload, headers=headers)
    if resp.status_code != 200:
        raise LLMError(f"{provider.name} HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise LLMError(f"{provider.name} returned an unexpected response shape")


async def generate_json(
    messages: list,
    validate: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    temperature: float = 0.8,
    max_tokens: int = 3000,
) -> Dict[str, Any]:
    """Return a validated JSON object from the first provider that produces one.

    `validate` may normalise the object and should raise ValueError when it is unusable.
    Each provider gets one retry with the error fed back before moving on.
    """
    providers = _configured_providers()
    if not providers:
        raise LLMError(
            "No LLM provider configured. Set GROQ_API_KEY (free at console.groq.com) "
            "or another provider key in the backend environment."
        )

    errors = []
    for provider in providers:
        convo = list(messages)
        for attempt in range(2):
            try:
                raw = await _call(provider, convo, temperature, max_tokens)
                obj = extract_json(raw)
                result = validate(obj) if validate else obj
                logger.info(f"LLM success via {provider.name} ({provider.model})")
                result.setdefault("_llm_provider", f"{provider.name}:{provider.model}")
                return result
            except (ValueError, json.JSONDecodeError) as e:
                errors.append(f"{provider.name}: invalid output ({e})")
                logger.warning(f"LLM {provider.name} gave invalid output (attempt {attempt + 1}): {e}")
                convo = list(messages) + [
                    {"role": "user", "content": f"Your previous reply was invalid: {e}. Reply again with ONLY the corrected JSON object."}
                ]
            except (LLMError, httpx.HTTPError) as e:
                errors.append(f"{provider.name}: {e}")
                logger.warning(f"LLM {provider.name} failed: {e}")
                break  # transport/quota error — go to next provider
    raise LLMError("All LLM providers failed: " + " | ".join(errors)[:600])
