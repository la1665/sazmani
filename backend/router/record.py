from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database.engine import async_session
from pathlib import Path
from datetime import datetime

from database.engine import get_db
from shared_resources import connections
from auth.authorization import get_admin_or_staff_user
from models.camera import DBCamera
from models.record import DBRecord, DBScheduledRecord
from crud.record import RecordOperation, ScheduledRecordOperation
from schema.user import UserInDB
from schema.record import RecordCreate, RecordInDB, RecordPagination
from socket_managment_nats_ import publish_message_to_nats

# Directory for recordings
BASE_UPLOAD_DIR = Path("uploads")
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"

record_router = APIRouter()

@record_router.get("/records/", response_model=RecordPagination)
async def get_records(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    camera_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user),
):
    """
    Get recorded video information.
    """
    record_op = RecordOperation(db)
    records = await record_op.get_all_records(page, page_size, camera_id)

    # Dynamically construct the base URL based on the request
    proto = request.headers.get("X-Forwarded-Proto", "http")
    base_url = str(request.base_url).split(":")[1].strip()  # Remove trailing slash if present
    nginx_base_url = f"{proto}:{base_url}" # Remove trailing slash if present

    return [
        {
            "id": record.id,
            "title": record.title,
            "camera_id": record.camera_id,
            "timestamp": record.timestamp,
            "video_url": f"{nginx_base_url}/uploads/recordings/{record.title}",
        }
        for record in records["records"]
    ]


# Endpoint to serve video files for download
@record_router.get("/records/download/{record_id}")
async def download_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user),
):
    """
    Download a recorded video by its ID.
    """
    async with db as session:
        query = await session.execute(select(DBRecord).where(DBRecord.id == record_id))
        record = query.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Construct the file path
        video_path = Path(RECORDINGS_DIR) / Path(record.video_url).name

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")

        # Serve the file with Content-Disposition: attachment
        return FileResponse(
            path=video_path,
            filename=record.title,
            media_type="video/mp4",  # Ensure correct media type
            headers={"Content-Disposition": f"attachment; filename={record.title}"}
        )


@record_router.post("/start_recording", status_code=200)
async def start_recording(
    camera_id: int,
    duration: int = 60,
    current_user: UserInDB=Depends(get_admin_or_staff_user),
):
    """
    API endpoint to start recording.
    """
    global connections
    async with async_session() as session:
        query = await session.execute(
            select(DBCamera).where(DBCamera.id == camera_id).options(selectinload(DBCamera.lpr))
        )
        db_camera = query.scalar_one_or_none()

        if not db_camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        lpr = db_camera.lpr
        if not (lpr and lpr.is_active):
            raise HTTPException(status_code=400, detail="LPR not active or not found")

        if lpr.id in connections:
            factory = connections[lpr.id]
            if factory.authenticated and factory.active_protocol:
                # Send the recording command to the server
                command_data = {
                    "commandType": "recording",
                    "cameraId": str(camera_id),
                    "duration": duration,
                }
                factory.active_protocol.send_command(command_data)
                return {"status": "success", "message": "Recording command sent"}
            else:
                raise HTTPException(status_code=500, detail="LPR server not authenticated or connected")
        else:
            raise HTTPException(status_code=500, detail="No active connection for LPR")



@record_router.get("/scheduled_recordings", status_code=200)
async def get_scheduled_recordings(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user),
):
    schedule_record_op = ScheduledRecordOperation(db)
    records = await schedule_record_op.get_all_scheduled_records(page, page_size)

    # Dynamically construct the base URL based on the request
    proto = request.headers.get("X-Forwarded-Proto", "http")
    base_url = str(request.base_url).split(":")[1].strip()  # Remove trailing slash if present
    nginx_base_url = f"{proto}:{base_url}" # Remove trailing slash if present

    return [
        {
            "id": record.id,
            "title": record.title,
            "camera_id": record.camera_id,
            "timestamp": record.timestamp,
            "video_url": f"{nginx_base_url}/uploads/recordings/{record.title}",
        }
        for record in records["records"]
    ]

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
