import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from router.record import process_scheduled_recordings

from database.engine import async_session, engine, ensure_tables_exist
from utils.db_utils import create_default_admin, initialize_defaults
from socket_managment_nats_ import connect_to_nats


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting lifespan")

    # Initialize database
    async with async_session() as session:
        await ensure_tables_exist()
        await create_default_admin(session)
        await initialize_defaults(session)

    # Start NATS connection
    nats_task = asyncio.create_task(connect_to_nats())

    # Scheduler for recurring tasks
    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_scheduled_recordings, "interval", seconds=60)
    scheduler.start()

    try:
        yield
    finally:
        # Cleanup
        nats_task.cancel()  # Cancel the NATS connection task
        await engine.dispose()
        print("[INFO] Database connection closed")
        print("[INFO] Lifespan ended")
