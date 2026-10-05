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
            # MongoDB returns naive datetimes that are UTC — label them so browsers
            # don't read them as local time (was off by +5:30 in India)
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
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


async def list_recent_tasks(limit: int = 20, active_only: bool = False) -> List[dict]:
    db = get_db()
    if db is None:
        return []
    query = {"status": {"$in": ["pending", "queued", "in_progress"]}} if active_only else {}
    cursor = db.video_tasks.find(query, {"generation_settings": 0}).sort("created_at", -1).limit(limit)
    return [_doc_to_dict(doc) async for doc in cursor]


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


# ── Users ────────────────────────────────────────────────────────────────────

async def create_user(email: str, password_hash: str, name: Optional[str] = None) -> dict:
    """Create a new user document in MongoDB Atlas."""
    db = get_db()
    clean_email = email.strip().lower()
    now = _utcnow()
    display_name = name.strip() if name and name.strip() else clean_email.split("@")[0].capitalize()
    doc = {
        "email": clean_email,
        "password_hash": password_hash,
        "name": display_name,
        "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={clean_email}",
        "tier": "free",
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
    }
    if db is None:
        return {"id": "offline_user", **doc, "created_at": now.isoformat()}
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def get_user_by_email(email: str) -> Optional[dict]:
    """Retrieve user by normalized email."""
    db = get_db()
    if db is None:
        return None
    clean_email = email.strip().lower()
    doc = await db.users.find_one({"email": clean_email})
    return _doc_to_dict(doc) if doc else None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Retrieve user by ObjectId string."""
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def update_user_last_login(user_id: str) -> None:
    """Update last_login_at timestamp."""
    db = get_db()
    if db is None:
        return
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login_at": _utcnow()}}
        )
    except Exception:
        pass


# ── AI Video Director / Video Plans ──────────────────────────────────────────

async def save_video_plan(plan: dict, project_id: Optional[str] = None, task_id: Optional[str] = None) -> str:
    """Save a generated VideoPlan to wan_video_plans collection."""
    db = get_db()
    now = _utcnow()
    doc = {
        **plan,
        "project_id": project_id,
        "task_id": task_id,
        "created_at": now,
        "updated_at": now,
    }
    if db is None:
        import uuid
        return str(uuid.uuid4())
    result = await db.wan_video_plans.insert_one(doc)
    return str(result.inserted_id)


async def get_video_plan(plan_id: str) -> Optional[dict]:
    """Retrieve a VideoPlan by its ID."""
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.wan_video_plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        return None
    return _doc_to_dict(doc) if doc else None


async def get_plan_by_task(task_id: str) -> Optional[dict]:
    """Retrieve a VideoPlan linked to a task_id."""
    db = get_db()
    if db is None:
        return None
    doc = await db.wan_video_plans.find_one({"task_id": task_id})
    return _doc_to_dict(doc) if doc else None


async def update_plan_scene(plan_id: str, scene_id: str, scene_data: Dict[str, Any]) -> bool:
    """Update a specific scene within a VideoPlan."""
    db = get_db()
    if db is None:
        return False
    try:
        plan = await db.wan_video_plans.find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return False
        scenes = plan.get("scenes", [])
        updated = False
        for s in scenes:
            if s.get("id") == scene_id:
                s.update(scene_data)
                updated = True
                break
        if updated:
            await db.wan_video_plans.update_one(
                {"_id": ObjectId(plan_id)},
                {"$set": {"scenes": scenes, "updated_at": _utcnow()}}
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating plan scene {scene_id} in {plan_id}: {e}")
        return False


# ── Character References ─────────────────────────────────────────────────────

async def save_character_ref(job_id: str, char_id: str, image_path: str) -> None:
    """Cache character reference image path."""
    db = get_db()
    if db is None:
        return
    try:
        await db.character_references.update_one(
            {"char_id": char_id},
            {"$set": {"job_id": job_id, "image_path": image_path, "updated_at": _utcnow()}},
            upsert=True
        )
    except Exception as e:
        logger.warning(f"Failed to cache character ref {char_id}: {e}")


async def get_character_ref(char_id: str) -> Optional[str]:
    """Retrieve cached character reference image path."""
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.character_references.find_one({"char_id": char_id})
        return doc.get("image_path") if doc else None
    except Exception:
        return None


