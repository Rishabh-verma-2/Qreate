"""One-shot and batch pipeline routes: topic(s) in → publish-ready videos out."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.database import crud
from app.database.connection import get_db
from app.schemas.schemas import BatchCreateRequest, ContentOptions, PipelineRunRequest
from app.api.routes.videos import ensure_capacity
from app.worker import queue

router = APIRouter(prefix="/api", tags=["Pipeline"])
logger = logging.getLogger(__name__)


def _require_db():
    if get_db() is None:
        raise HTTPException(status_code=503, detail="Database unavailable — the job queue needs MongoDB")


async def _queue_topic(topic: str, options: ContentOptions, batch_id: str = None) -> dict:
    project = await crud.create_project({
        "name": (options.title or topic)[:200],
        "topic": topic,
        "description": "Auto-created by the Qreate pipeline",
        "status": "active",
        "batch_id": batch_id,
    })
    return await queue.enqueue({
        "project_id": project["id"],
        "batch_id": batch_id,
        "topic": topic,
        "options": options.model_dump(),
        "generation_settings": {"aspect_ratio": "9:16", "resolution": "1080x1920", "engine": "stock-footage"},
    })


@router.post("/pipeline/run", response_model=dict, status_code=202)
async def run_pipeline(body: PipelineRunRequest):
    """Topic → script → voice → footage → captions → video, fully automatic."""
    _require_db()
    await ensure_capacity()
    options = ContentOptions(**body.model_dump(exclude={"topic"}))
    task = await _queue_topic(body.topic.strip(), options)
    return {"data": task, "message": "Pipeline started"}


@router.post("/batches", response_model=dict, status_code=202)
async def create_batch(body: BatchCreateRequest):
    """Queue one full pipeline run per topic. Topics render in parallel across workers."""
    _require_db()
    topics = [t.strip() for t in body.topics if t and t.strip()]
    # De-duplicate while keeping order
    topics = list(dict.fromkeys(topics))
    if not topics:
        raise HTTPException(status_code=422, detail="Provide at least one topic")
    max_batch = get_settings().MAX_BATCH_SIZE
    if len(topics) > max_batch:
        raise HTTPException(status_code=422, detail=f"A batch can have at most {max_batch} topics")
    await ensure_capacity(len(topics))

    batch = await crud.create_batch({
        "name": body.name or f"Batch of {len(topics)}",
        "topics": topics,
        "options": body.options.model_dump(),
        "task_ids": [],
    })
    task_ids = [(await _queue_topic(t, body.options, batch["id"]))["id"] for t in topics]
    await crud.update_batch(batch["id"], {"task_ids": task_ids})
    batch["task_ids"] = task_ids
    logger.info(f"Batch {batch['id']} queued with {len(topics)} topics")
    return {"data": batch, "message": f"Queued {len(topics)} videos"}


def _summarise(tasks: list) -> dict:
    counts = {}
    for t in tasks:
        counts[t.get("status", "unknown")] = counts.get(t.get("status", "unknown"), 0) + 1
    done = counts.get("completed", 0) + counts.get("failed", 0)
    return {"total": len(tasks), "done": done, "counts": counts}


@router.get("/batches", response_model=dict)
async def list_batches():
    batches = await crud.list_batches(limit=20)
    for b in batches:
        b["summary"] = _summarise(await crud.list_tasks_for_batch(b["id"]))
    return {"data": batches}


@router.get("/batches/{batch_id}", response_model=dict)
async def get_batch(batch_id: str):
    batch = await crud.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    tasks = await crud.list_tasks_for_batch(batch_id)
    videos = {v.get("task_id"): v for v in await crud.list_videos_for_batch(batch_id)}
    items = [{"task": t, "video": videos.get(t["id"])} for t in tasks]
    return {"data": {**batch, "items": items, "summary": _summarise(tasks)}}


@router.get("/queue/stats", response_model=dict)
async def get_queue_stats():
    s = get_settings()
    return {
        "data": {
            "by_status": await queue.queue_stats(),
            "embedded_worker": s.EMBEDDED_WORKER,
            "worker_concurrency": s.WORKER_CONCURRENCY,
            "max_queue_depth": s.MAX_QUEUE_DEPTH,
        }
    }
