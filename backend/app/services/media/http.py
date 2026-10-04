"""Shared HTTP client, bounded downloads and a small TTL cache for search APIs."""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "QreateBot/2.0 (+https://github.com/Rishabh-verma-2/Qreate)"
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024

_client: Optional[httpx.AsyncClient] = None


def client() -> httpx.AsyncClient:
    """Process-wide pooled client (connection reuse matters under batch load)."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json(url: str, *, params: dict = None, headers: dict = None) -> Optional[Any]:
    """GET JSON with one retry on 429/5xx. Returns None on failure."""
    for attempt in range(2):
        try:
            resp = await client().get(url, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503) and attempt == 0:
                await asyncio.sleep(1.5)
                continue
            logger.info(f"GET {url} -> HTTP {resp.status_code}")
            return None
        except (httpx.HTTPError, ValueError) as e:
            logger.info(f"GET {url} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(1.0)
    return None


async def download(url: str, dest: str, min_bytes: int = 10_000, headers: dict = None, timeout_seconds: float = 20.0) -> bool:
    """Stream `url` to `dest`. Rejects tiny (error pages) and oversized files."""
    try:
        async with client().stream("GET", url, headers=headers, timeout=httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 6.0))) as resp:
            if resp.status_code != 200:
                return False
            size = 0
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(256 * 1024):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_BYTES:
                        logger.info(f"Download too large, skipped: {url[:80]}")
                        return False
                    f.write(chunk)
        return size >= min_bytes
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        logger.info(f"Download failed {url[:80]}: {e}")
        return False


class TTLCache:
    """Tiny in-process LRU+TTL cache — saves free-tier API quota on repeated queries."""

    def __init__(self, maxsize: int = 512, ttl: float = 6 * 3600):
        self.maxsize, self.ttl = maxsize, ttl
        self._data: "OrderedDict[str, tuple]" = OrderedDict()

    def get(self, key: str):
        item = self._data.get(key)
        if not item:
            return None
        ts, value = item
        if time.monotonic() - ts > self.ttl:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value) -> None:
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)
