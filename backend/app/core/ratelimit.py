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
    """Raise 429 if `owner` already used its hourly quota for `kind` ("video" | "script").

    Returns the owner key so callers can store it on the new document.
    """
    s = get_settings()
    owner = owner_of(request)
    limit = s.RATE_LIMIT_VIDEOS_PER_HOUR if kind == "video" else s.RATE_LIMIT_SCRIPTS_PER_HOUR
    db = get_db()
    if db is None or limit <= 0:
        return owner
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    collection = db.video_tasks if kind == "video" else db.scripts
    used = await collection.count_documents({"owner": owner, "created_at": {"$gte": since}})
    if used + cost > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Hourly limit reached ({limit} {kind}s per hour). Please try again later.",
        )
    return owner
