"""Standalone worker: `python -m app.worker`.

Run as many of these as you like (on any machine) against the same MongoDB to scale
rendering horizontally. Set EMBEDDED_WORKER=false on the API when you do.
"""

import asyncio
import logging
import signal

from app.core.config import get_settings
from app.database.connection import close_db, connect_db, get_db
from app.services.media.http import close_client
from app.worker.runner import WorkerPool

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s")


async def main():
    await connect_db()
    if get_db() is None:
        raise SystemExit("MongoDB is required for workers (set MONGODB_URI)")
    pool = WorkerPool(get_settings().WORKER_CONCURRENCY)
    pool.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    await pool.stop()
    await close_client()
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
