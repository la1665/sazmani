from typing import AsyncGenerator
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from settings import settings


DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    echo_pool=True,
    future=True,
    pool_size=5,  # Lower to reduce pressure on the database
    max_overflow=10,  # Allow some flexibility for overflow
    pool_recycle=3600,
    pool_timeout=30,  # Prevent blocking indefinitely if the pool is exhausted
)
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

nats_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    echo_pool=True,
    future=True,
    pool_size=5,  # Lower to reduce pressure on the database
    max_overflow=10,  # Allow some flexibility for overflow
    pool_recycle=3600,
    pool_timeout=30,  # Prevent blocking indefinitely if the pool is exhausted
)
nats_session = async_sessionmaker(
    bind=nats_engine,
    expire_on_commit=False,
    class_=AsyncSession
)
Base = declarative_base()


def table_exists(engine, table_name):
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()



# async def initialize_async_database(engine: AsyncEngine):
#     """
#     Asynchronous initialization of the database schema.
#     """
#     async with engine.begin() as conn:
#         print("Initializing database schema asynchronously...")
#         await conn.run_sync(Base.metadata.create_all)
#         print("Database schema initialized successfully!")


async def ensure_tables_exist():
    """Ensure all tables defined in Base are created."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("All tables created successfully.")
    except SQLAlchemyError as e:
        print(f"Error creating tables: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:

    async with async_session() as session:
        yield session
