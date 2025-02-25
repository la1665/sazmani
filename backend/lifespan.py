import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.recording_processor import process_scheduled_recordings

from database.engine import async_session, engine, ensure_tables_exist
from utils.db_utils import create_default_admin, initialize_defaults
from socket_managment_nats_ import connect_to_nats
from search_service.search_config import (
    user_search, building_search,
    gate_search, camera_search,
    lpr_search, traffic_search,
    camera_setting_search, lpr_setting_search,
    guest_search,
)
from redis_cache import redis_cache
from utils.middlewares import security_middleware


async def initialize_search_services():
    await user_search.initialize_index()
    await guest_search.initialize_index()
    await building_search.initialize_index()
    await gate_search.initialize_index()
    await camera_search.initialize_index()
    await camera_setting_search.initialize_index()
    await lpr_search.initialize_index()
    await lpr_setting_search.initialize_index()
    await traffic_search.initialize_index()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting lifespan")

    await redis_cache.init_cache()
    await ensure_tables_exist()
    await initialize_search_services()

    # Initialize database
    async with async_session() as session:
        await ensure_tables_exist()
        await create_default_admin(session)
        await initialize_defaults(session)

    # Setup Redis for SecurityMiddleware
    await security_middleware.setup_redis()

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
        await redis_cache.redis.close()
        await security_middleware.redis.close()
        nats_task.cancel()  # Cancel the NATS connection task
        scheduler.shutdown()
        await engine.dispose()
        print("[INFO] Database connection closed")
        print("[INFO] Lifespan ended")
