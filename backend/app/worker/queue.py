"""MongoDB-backed job queue (the `video_tasks` collection).

Workers atomically claim the oldest queued job with find_one_and_update and hold a
lease that they renew while working. If a worker dies, its lease expires and another
worker picks the job up. Any number of worker processes can share one database,
so throughput scales by adding instances — no Redis or paid queue needed.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pymongo import ReturnDocument

from app.core.config import get_settings
from app.database import crud
from app.database.connection import get_db

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "in_progress")
# Other engines (PurffleShorts/Agnes) also use the "queued" status for their own
# background tasks — workers only ever claim jobs tagged with this queue name.
QUEUE_NAME = "qreate"


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue(data: Dict[str, Any]) -> dict:
    """Create a queued job. `data` needs project_id and either script_id or topic+options."""
    return await crud.create_video_task({
        "queue": QUEUE_NAME,
        "script_id": None,
        "batch_id": None,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "attempts": 0,
        "error_message": None,
        "completed_at": None,
        **data,
    })


async def queue_depth() -> int:
    db = get_db()
    if db is None:
        return 0
    return await db.video_tasks.count_documents({"queue": QUEUE_NAME, "status": {"$in": list(ACTIVE_STATUSES)}})


async def queue_stats() -> Dict[str, int]:
    db = get_db()
    if db is None:
        return {}
    pipeline = [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]
    return {row["_id"] or "unknown": row["n"] async for row in db.video_tasks.aggregate(pipeline)}


async def claim(worker_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    s = get_settings()
    now = _now()
    doc = await db.video_tasks.find_one_and_update(
        {
            "queue": QUEUE_NAME,
            "$or": [
                {"status": "queued"},
                # Abandoned by a crashed/restarted worker
                {"status": "in_progress", "lease_until": {"$lt": now}, "attempts": {"$lt": s.JOB_MAX_ATTEMPTS}},
            ]
        },
        {
            "$set": {
                "status": "in_progress",
                "stage": "starting",
                "worker_id": worker_id,
                "lease_until": now + timedelta(seconds=s.JOB_LEASE_SECONDS),
                "started_at": now,
                "updated_at": now,
            },
            "$inc": {"attempts": 1},
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    return crud._doc_to_dict(doc) if doc else None


async def renew(job_id: str, worker_id: str, **fields) -> None:
    """Extend the lease (and optionally update progress/stage) for a job we own."""
    db = get_db()
    if db is None:
        return
    from bson import ObjectId
    now = _now()
    await db.video_tasks.update_one(
        {"_id": ObjectId(job_id), "worker_id": worker_id},
        {"$set": {**fields, "lease_until": now + timedelta(seconds=get_settings().JOB_LEASE_SECONDS), "updated_at": now}},
    )


async def fail_exhausted() -> int:
    """Mark jobs whose lease expired after the final attempt as failed."""
    db = get_db()
    if db is None:
        return 0
    s = get_settings()
    res = await db.video_tasks.update_many(
        {"queue": QUEUE_NAME, "status": "in_progress", "lease_until": {"$lt": _now()}, "attempts": {"$gte": s.JOB_MAX_ATTEMPTS}},
        {"$set": {"status": "failed", "stage": "failed", "error_message": "Worker stopped repeatedly while rendering this job", "completed_at": _now()}},
    )
    return res.modified_count
