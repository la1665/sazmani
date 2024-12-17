from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database.engine import async_session

from shared_resources import connections
from models.camera import DBCamera
from database.engine import get_db
from models.record import DBRecord
from crud.record import RecordOperation

record_router = APIRouter()

@record_router.get("/records/")
async def get_records(camera_id: int = None, db: AsyncSession = Depends(get_db)):
    """
    Get recorded video information.
    """
    record_op = RecordOperation(db)
    records = await record_op.get_records(camera_id=camera_id)
    return [{"id": record.id, "title": record.title, "camera_id": record.camera_id, "timestamp": record.timestamp, "video_url": record.video_url} for record in records]


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
                    "cameraId": camera_id,
                    "duration": duration,
                }
                factory.active_protocol.send_command(command_data)
                return {"status": "success", "message": "Recording command sent"}
            else:
                raise HTTPException(status_code=500, detail="LPR server not authenticated or connected")
        else:
            raise HTTPException(status_code=500, detail="No active connection for LPR")
