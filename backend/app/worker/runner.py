"""Worker pool: claims queued jobs and runs the full pipeline for each."""

import asyncio
import logging
import os
import random
import socket
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.core.config import get_settings
from app.database import crud
from app.services.pipeline import produce_video
from app.schemas.schemas import style_from
from app.services.research import gather_research, research_sources
from app.services.script.generator import generate_script, script_fields_for_db
from app.worker import queue

logger = logging.getLogger(__name__)

IDLE_POLL_SECONDS = 2.0


def _now():
    return datetime.now(timezone.utc)


async def _ensure_script(job: dict, report) -> dict:
    """Return the job's script, writing one with the LLM first if the job only has a topic."""
    if job.get("script_id"):
        script = await crud.get_script(job["script_id"])
        if script:
            return script

    opts = job.get("options") or {}
    topic = job.get("topic") or opts.get("topic")
    if not topic:
        raise ValueError("Job has neither a script nor a topic")

    await report(4, "researching trends")
    research = await gather_research(topic, opts.get("language", "English"))
    await report(8, "writing script")
    generated = await generate_script(
        topic=topic,
        duration_seconds=int(opts.get("duration_seconds", 30)),
        language=opts.get("language", "English"),
        tone=opts.get("tone", "energetic"),
        audience=opts.get("audience", "general"),
        title=opts.get("title"),
        additional_instructions=opts.get("additional_instructions"),
        has_user_media=bool(opts.get("user_media")),
        research=research,
        video_format=opts.get("video_format", "auto"),
        visual_style=opts.get("visual_style", "real"),
        people_focus=opts.get("people_focus", True),
    )
    script = await crud.create_script({
        "project_id": job["project_id"],
        "owner": job.get("owner"),
        **script_fields_for_db(generated),
        "language": opts.get("language", "English"),
        "tone": opts.get("tone", "energetic"),
        "audience": opts.get("audience", "general"),
        "duration_seconds": int(opts.get("duration_seconds", 30)),
        "original_prompt": topic,
        "additional_instructions": opts.get("additional_instructions"),
        "voice_gender": opts.get("voice_gender", "male"),
        "user_media": opts.get("user_media") or [],
        "style": style_from(opts),
        "approved": True,
        "version": 1,
    })
    await crud.update_video_task(job["id"], {"script_id": script["id"]})
    return script


async def process_job(job: dict, worker_id: str) -> None:
    job_id = job["id"]
    s = get_settings()

    async def report(progress: int, stage: str):
        await queue.renew(job_id, worker_id, progress=progress, stage=stage)

    async def heartbeat():
        while True:
            await asyncio.sleep(max(s.JOB_LEASE_SECONDS / 3, 5))
            await queue.renew(job_id, worker_id)

    hb = asyncio.create_task(heartbeat())
    try:
        script = await _ensure_script(job, report)
        await report(15, "preparing")
        result = await produce_video(script, job_id, job["project_id"], report)

        video = await crud.create_generated_video({
            "project_id": job["project_id"],
            "script_id": script["id"],
            "task_id": job_id,
            "batch_id": job.get("batch_id"),
            "title": script.get("title"),
            "hook": script.get("hook"),
            "post": script.get("post") or {},
            "inspiration": research_sources(script.get("research") or {}),
            "original_url": result["cloudinary_url"],
            "file_format": "mp4",
            **result,
        })
        await crud.update_video_task(job_id, {
            "status": "completed",
            "stage": "done",
            "progress": 100,
            "completed_at": _now(),
            "generated_video_id": video["id"],
            "cloudinary_url": result["cloudinary_url"],
            "thumbnail_url": result.get("thumbnail_url"),
            "title": script.get("title"),
        })
        logger.info(f"[{worker_id}] job {job_id} completed")
    except asyncio.CancelledError:
        # Shutting down: hand the job back so another worker (or the restart) resumes it
        await crud.update_video_task(job_id, {"status": "queued", "stage": "requeued", "worker_id": None})
        raise
    except Exception as e:
        logger.exception(f"[{worker_id}] job {job_id} failed")
        retry = int(job.get("attempts", 1)) < s.JOB_MAX_ATTEMPTS
        await crud.update_video_task(job_id, {
            "status": "queued" if retry else "failed",
            "stage": "retrying" if retry else "failed",
            "error_message": str(e)[:500],
            "worker_id": None,
            **({} if retry else {"completed_at": _now()}),
        })
    finally:
        hb.cancel()


class WorkerPool:
    def __init__(self, concurrency: int):
        self.concurrency = max(concurrency, 1)
        self.base_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:4]}"
        self._tasks: List[asyncio.Task] = []

    async def _loop(self, n: int):
        worker_id = f"{self.base_id}-w{n}"
        logger.info(f"Worker {worker_id} started")
        while True:
            try:
                if n == 0:
                    await queue.fail_exhausted()
                job = await queue.claim(worker_id)
                if job is None:
                    await asyncio.sleep(IDLE_POLL_SECONDS + random.random())
                    continue
                logger.info(f"[{worker_id}] claimed job {job['id']} (attempt {job.get('attempts')})")
                await process_job(job, worker_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(f"Worker {worker_id} loop error")
                await asyncio.sleep(5)

    def start(self):
        self._tasks = [asyncio.create_task(self._loop(i)) for i in range(self.concurrency)]

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []


_pool: Optional[WorkerPool] = None


def start_embedded_pool() -> None:
    global _pool
    _pool = WorkerPool(get_settings().WORKER_CONCURRENCY)
    _pool.start()


async def stop_embedded_pool() -> None:
    if _pool:
        await _pool.stop()
