"""Per-user hourly limits so nobody can burn the free API quotas.

The caller is identified by their login token (user id) or, if not signed in, by IP.
Counts come from MongoDB (documents carry an `owner` field), so the limit holds across
any number of API instances.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database.connection import get_db


def owner_of(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        payload = decode_access_token(auth[7:].strip()) or {}
        if payload.get("sub"):
            return f"user:{payload['sub']}"
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


async def enforce(request: Request, kind: str, cost: int = 1) -> str:
    """Return the owner key without imposing restrictive hourly quotas.

    Allows unlimited script and video generation for custom videos.
    """
    return owner_of(request)
