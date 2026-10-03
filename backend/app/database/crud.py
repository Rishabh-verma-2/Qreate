"""MongoDB CRUD helpers for all collections."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.database.connection import get_db

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _doc_to_dict(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return {}
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _doc_to_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _doc_to_dict(v) if isinstance(v, dict) else str(v) if isinstance(v, ObjectId) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


# ── Projects ─────────────────────────────────────────────────────────────────

async def create_project(data: Dict[str, Any]) -> dict:
    db = get_db()
    if db is None:
        return {"id": "offline", **data, "created_at": _utcnow().isoformat()}
    now = _utcnow()
    doc = {**data, "created_at": now, "updated_at": now, "status": data.get("status", "active")}
    result = await db.projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def get_project(project_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def list_projects(limit: int = 50) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.projects.find({}).sort("created_at", -1).limit(limit)
    return [_doc_to_dict(doc) async for doc in cursor]


async def update_project(project_id: str, data: Dict[str, Any]) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        update = {"$set": {**data, "updated_at": _utcnow()}}
        result = await db.projects.find_one_and_update(
            {"_id": ObjectId(project_id)}, update, return_document=True
        )
    except Exception:
        return None
    return _doc_to_dict(result) if result else None


async def delete_project(project_id: str) -> bool:
    db = get_db()
    if db is None:
        return False
    try:
        result = await db.projects.delete_one({"_id": ObjectId(project_id)})
        return result.deleted_count > 0
    except Exception:
        return False


# ── Scripts ───────────────────────────────────────────────────────────────────

async def create_script(data: Dict[str, Any]) -> dict:
    db = get_db()
    if db is None:
        return {"id": "offline", **data, "created_at": _utcnow().isoformat()}
    now = _utcnow()
    doc = {**data, "created_at": now, "updated_at": now, "version": data.get("version", 1)}
    result = await db.scripts.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def get_script(script_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.scripts.find_one({"_id": ObjectId(script_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def list_scripts_for_project(project_id: str) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.scripts.find({"project_id": project_id}).sort("created_at", -1)
    return [_doc_to_dict(doc) async for doc in cursor]


async def update_script(script_id: str, data: Dict[str, Any]) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        update = {"$set": {**data, "updated_at": _utcnow()}}
        result = await db.scripts.find_one_and_update(
            {"_id": ObjectId(script_id)}, update, return_document=True
        )
    except Exception:
        return None
    return _doc_to_dict(result) if result else None


# ── Video Tasks ───────────────────────────────────────────────────────────────

async def create_video_task(data: Dict[str, Any]) -> dict:
    db = get_db()
    if db is None:
        return {"id": "offline", **data, "created_at": _utcnow().isoformat()}
    now = _utcnow()
    doc = {**data, "created_at": now, "updated_at": now}
    result = await db.video_tasks.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def get_video_task(task_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.video_tasks.find_one({"_id": ObjectId(task_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def update_video_task(task_id: str, data: Dict[str, Any]) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        update = {"$set": {**data, "updated_at": _utcnow()}}
        result = await db.video_tasks.find_one_and_update(
            {"_id": ObjectId(task_id)}, update, return_document=True
        )
    except Exception:
        return None
    return _doc_to_dict(result) if result else None


async def list_tasks_for_project(project_id: str) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.video_tasks.find({"project_id": project_id}).sort("created_at", -1)
    return [_doc_to_dict(doc) async for doc in cursor]


# ── Generated Videos ──────────────────────────────────────────────────────────

async def create_generated_video(data: Dict[str, Any]) -> dict:
    db = get_db()
    if db is None:
        return {"id": "offline", **data, "created_at": _utcnow().isoformat()}
    now = _utcnow()
    doc = {**data, "created_at": now}
    result = await db.generated_videos.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def list_generated_videos(limit: int = 50) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.generated_videos.find({}).sort("created_at", -1).limit(limit)
    return [_doc_to_dict(doc) async for doc in cursor]


async def list_videos_for_project(project_id: str) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.generated_videos.find({"project_id": project_id}).sort("created_at", -1)
    return [_doc_to_dict(doc) async for doc in cursor]


async def get_generated_video(video_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.generated_videos.find_one({"_id": ObjectId(video_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


# ── Batches ───────────────────────────────────────────────────────────────────

async def create_batch(data: Dict[str, Any]) -> dict:
    db = get_db()
    if db is None:
        return {"id": "offline", **data}
    doc = {**data, "created_at": _utcnow()}
    result = await db.batches.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def update_batch(batch_id: str, data: Dict[str, Any]) -> None:
    db = get_db()
    if db is None:
        return
    await db.batches.update_one({"_id": ObjectId(batch_id)}, {"$set": data})


async def get_batch(batch_id: str) -> Optional[dict]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.batches.find_one({"_id": ObjectId(batch_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def list_batches(limit: int = 20) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.batches.find({}).sort("created_at", -1).limit(limit)
    return [_doc_to_dict(doc) async for doc in cursor]


async def list_tasks_for_batch(batch_id: str) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.video_tasks.find({"batch_id": batch_id}).sort("created_at", 1)
    return [_doc_to_dict(doc) async for doc in cursor]


async def list_videos_for_batch(batch_id: str) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    cursor = db.generated_videos.find({"batch_id": batch_id})
    return [_doc_to_dict(doc) async for doc in cursor]
