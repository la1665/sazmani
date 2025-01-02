from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database.engine import async_session
from pathlib import Path

from shared_resources import connections
from models.camera import DBCamera
from database.engine import get_db
from models.record import DBRecord
from crud.record import RecordOperation


# Directory for recordings
BASE_UPLOAD_DIR = Path("uploads")
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"

record_router = APIRouter()

@record_router.get("/records/")
async def get_records(request: Request, camera_id: int = None, db: AsyncSession = Depends(get_db)):
    """
    Get recorded video information.
    """
    record_op = RecordOperation(db)
    records = await record_op.get_records(camera_id=camera_id)

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
        for record in records
    ]


# Endpoint to serve video files for download
@record_router.get("/records/download/{record_id}")
async def download_record(record_id: int, db: AsyncSession = Depends(get_db)):
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
async def start_recording(camera_id: int, duration: int = 60):
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
