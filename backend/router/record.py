import os
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pathlib import Path
from datetime import datetime
from typing import Optional

from database.engine import async_session, get_db
from settings import settings
from auth.authorization import get_admin_or_staff_user
from models.camera import DBCamera
from models.record import DBRecord, DBScheduledRecord
from crud.record import RecordOperation, ScheduledRecordOperation
from schema.user import UserInDB
from schema.record import RecordCreate, RecordInDB, RecordPagination
from schema.schedule_record import ScheduleRecordCreate
from socket_managment_nats_ import publish_message_to_nats

# Directory for recordings
BASE_UPLOAD_DIR = Path("uploads")
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"

record_router = APIRouter(
    prefix="/v1/records",
    tags=["records"],
)

@record_router.get("/records/", status_code=status.HTTP_200_OK)
async def get_records(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    camera_id: Optional[int] = None,
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

    records["records"] = [
        {
            "id": record.id,
            "title": record.title,
            "camera_id": record.camera_id,
            "timestamp": record.timestamp,
            "video_url": f"{nginx_base_url}/uploads/recordings/{record.title}",
        }
        for record in records["records"]
    ]
    return records



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
    duration: int = 60,  # Default 60s, max 1 hour
    start_time: datetime = None,
    title: str = "Recording"
):
    """
    Starts an **immediate** recording if `start_time` is **None**,
    or **schedules** a recording for a future time.
    """

    async with async_session() as session:
        # Fetch camera with its LPR
        query = await session.execute(
            select(DBCamera).where(DBCamera.id == camera_id).options(selectinload(DBCamera.lpr))
        )
        db_camera = query.scalar_one_or_none()

        if not db_camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        # Validate LPR (License Plate Recognition system)
        lpr = db_camera.lpr
        if not lpr or not lpr.is_active:
            raise HTTPException(status_code=400, detail="LPR system is not active or not found for this camera")

        # Handle **Immediate Recording**
        if start_time is None:
            return await process_immediate_recording(session, lpr.id, camera_id, duration, title)

        # Handle **Scheduled Recording**
        else:
            return await process_scheduled_recording(session, camera_id, duration, title, start_time, db_camera.name)


async def process_immediate_recording(session: AsyncSession, lpr_id: int, camera_id: int, duration: int, title: str):
    """
    Handles immediate recording logic.
    """
    # Generate file path for recording
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    recording_filename = f"{camera_id}_{timestamp}.mp4"

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
        "cameraId": str(camera_id),
        "duration": duration,
        "video_address": file_path
    }

    try:
        # Publish to NATS
        await publish_message_to_nats(nats_payload, lpr_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish NATS message: {str(e)}")


    return {
        "status": "success",
        "message": "Immediate recording started"
    }


async def process_scheduled_recording(session: AsyncSession, camera_id: int, duration: int, title: str, start_time: datetime, camera_name: str):
    """
    Handles scheduled recording logic.
    """
    # Validate start_time (must be in the future)
    if start_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    # Auto-generate title if not provided
    if title == "Recording":
        title = f"Scheduled Recording for {camera_name} at {start_time.isoformat()}"

    # Schedule the recording
    scheduled_record_operation = ScheduledRecordOperation(session)
    scheduled_record = await scheduled_record_operation.create_scheduled_record(
        ScheduleRecordCreate(
            title=title,
            camera_id=camera_id,
            scheduled_time=start_time,
            duration=duration
        )
    )

    return {
        "status": "success",
        "message": "Recording scheduled successfully",
        "scheduledTime": start_time.isoformat(),
        "recordId": scheduled_record.id
    }



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
