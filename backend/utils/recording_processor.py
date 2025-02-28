import os
from pathlib import Path

import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from sqlalchemy.orm import selectinload

from database.engine import async_session
from models import DBCamera
from models.record import DBScheduledRecord
from settings import settings
from socket_managment_nats_ import publish_message_to_nats


async def process_scheduled_recordings():
    """
    Check and process scheduled recordings that are due to start.
    """
    async with async_session() as session:
        # Fetch all unprocessed scheduled recordings with a start time <= current time
        tehran_tz = pytz.timezone('Asia/Tehran')

        current_time = datetime.now(tehran_tz)
        query = select(DBScheduledRecord).where(
            DBScheduledRecord.scheduled_time <= current_time,
            DBScheduledRecord.is_processed == False
        )
        result = await session.execute(query)
        scheduled_records = result.scalars().all()

        for record in scheduled_records:
            try:
                query = await session.execute(
                    select(DBCamera).where(DBCamera.id == record.camera_id).options(selectinload(DBCamera.lpr))
                )
                db_camera = query.scalar_one_or_none()

                if not db_camera:
                    raise print("Camera not found")

                # Validate LPR (License Plate Recognition system)
                lpr = db_camera.lpr
                if not lpr or not lpr.is_active:
                    raise print("LPR system is not active or not found for this camera")
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                recording_filename = f"{record.camera_id}_{timestamp}.mp4"

                # Define base upload directory
                CURRENT_DIR = Path(__file__).resolve().parent
                PROJECT_ROOT = CURRENT_DIR.parent
                relative_upload_dir = settings.BASE_UPLOAD_DIR
                BASE_UPLOAD_DIR = PROJECT_ROOT / relative_upload_dir
                RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
                RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

                file_path = os.path.join(RECORDINGS_DIR, recording_filename)

                # Prepare NATS message
                nats_payload = {
                    "commandType": "recording",
                    "cameraId": str(record.camera_id),
                    "duration": record.duration,
                    "video_address": file_path
                }

                try:
                    # Publish to NATS
                    await publish_message_to_nats(nats_payload, lpr.id)
                except Exception as e:
                    raise print(f"Failed to publish NATS message: {str(e)}")


                record.is_processed = True
                session.add(record)
                await session.commit()

                print(f"Started recording for scheduled record ID: {record.id}")

            except Exception as e:
                print(f"Failed to process scheduled record ID: {record.id}, Error: {str(e)}")
