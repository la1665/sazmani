from fastapi import FastAPI
from contextlib import asynccontextmanager

from database.engine import engine, Base, async_session
from utils.db_utils import create_default_admin, initialize_defaults


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting lifespan")

    async with async_session() as session:
        await create_default_admin(session)
        await initialize_defaults(session)

    yield

    await engine.dispose()
    print("Database connection closed")
    print("[INFO] Lifespan ended")
