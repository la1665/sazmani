from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from database.engine import async_session
from models.record import DBScheduledRecord
from socket_managment_nats_ import publish_message_to_nats


async def process_scheduled_recordings():
    """
    Check and process scheduled recordings that are due to start.
    """
    async with async_session() as session:
        # Fetch all unprocessed scheduled recordings with a start time <= current time
        query = select(DBScheduledRecord).where(
            DBScheduledRecord.scheduled_time <= datetime.utcnow(),
            DBScheduledRecord.is_processed == False
        )
        result = await session.execute(query)
        scheduled_records = result.scalars().all()

        for record in scheduled_records:
            try:
                # Build NATS payload
                nats_payload = {
                    "commandType": "recording",
                    "cameraId": str(record.camera_id),
                    "duration": record.duration,
                }

                # Send the message to NATS
                await publish_message_to_nats(nats_payload, record.camera_id)
                record.is_processed = True
                session.add(record)
                await session.commit()

                print(f"Started recording for scheduled record ID: {record.id}")

            except Exception as e:
                print(f"Failed to process scheduled record ID: {record.id}, Error: {str(e)}")
