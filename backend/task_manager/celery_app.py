import asyncio
from celery import Celery
from database.engine import async_session
from crud.traffic import TrafficOperation
from schema.traffic import TrafficCreate
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.engine import Base
from database.engine import DATABASE_URL

# Configure the Celery app
celery = Celery(
    "sazman_tasks",
    broker="redis://redis:6379/0",  # Redis as the message broker
    backend="redis://redis:6379/0",  # Redis as the result backend
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Create a new session factory for each task
engine = create_async_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    pool_size=10,  # Adjust based on your workload
    max_overflow=20,
)
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

@celery.task
def save_plates_data_to_db(camera_id, timestamp, cars):
    async def save_data():
        async with async_session_factory() as session:
            try:
                traffic_operation = TrafficOperation(session)
                for car in cars:
                    traffic_data = TrafficCreate(
                        plate_number=car.get("plate", {}).get("plate", "Unknown"),
                        ocr_accuracy=car.get("ocr_accuracy", "Unknown"),
                        vision_speed=car.get("vision_speed", 0.0),
                        plate_image_path=car.get("plate", {}).get("plate_image", ""),
                        timestamp=timestamp,
                        camera_id=camera_id,
                    )
                    await traffic_operation.create_traffic(traffic_data)
                    # await session.commit()
                print(f"[INFO] Successfully stored traffic data for camera {camera_id}.")
            except Exception as exc:
                await session.rollback()
                print(f"[ERROR] Failed to store traffic data: {exc}")
            finally:
                await session.close()

    asyncio.run(save_data())

@celery.task
def add_numbers(a, b):
    return a + b
