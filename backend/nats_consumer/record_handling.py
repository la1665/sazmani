import asyncio
import datetime
import os
import json
import numpy as np
import cv2
from pathlib import Path

from settings import settings
# from database.engine import async_session
from database.engine import nats_session
from models.record import DBRecord

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
relative_upload_dir = settings.BASE_UPLOAD_DIR

BASE_UPLOAD_DIR = PROJECT_ROOT / relative_upload_dir

RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

BUFFER_LIMIT = 20
FPS = 5

camera_recordings = {}
frame_buffers = {}

async def save_recording_metadata(title, camera_id, file_path):
    async with nats_session() as session:
        try:
            record = DBRecord(
                title=title,
                camera_id=int(camera_id),
                timestamp=datetime.datetime.now(),
                video_url=str(file_path)
            )
            session.add(record)
            await session.commit()
            print(f"Recording metadata saved to database: {title}")
        except Exception as db_error:
            await session.rollback()
            print(f"[ERROR] Failed to save recording to database: {db_error}")

async def handle_recording(msg):
    try:
        message = json.loads(msg.data.decode())
        message_body = message.get("messageBody", {})
    except Exception as exp:
        print(f"Extract recording message exception: {exp}")
        return

    frame_bytes = message_body.get("frame")
    camera_id = message_body.get("camera_id")
    end_recording = message_body.get("end_recording")

    if not frame_bytes and not end_recording:
        print("Invalid message body")
        return

    # End Recording
    if end_recording:
        file_path = message_body["video_address"]#finalize_recording(camera_id)
        if file_path:
            title = os.path.basename(file_path)
            asyncio.create_task(save_recording_metadata(title, camera_id, file_path))
        return

    # Decode frame
    try:
        if isinstance(frame_bytes, list):
            frame_bytes = bytes(frame_bytes)
        arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # BGR format
    except Exception as e:
        print(f"Failed to decode frame: {e}")
        return

    if camera_id not in camera_recordings:
        initialize_camera_recording(camera_id, frame.shape[1], frame.shape[0])

    # Put frame on the queue
    try:
        await frame_buffers[camera_id].put(frame)
    except Exception as e:
        print(f"Error putting frame in queue: {e}")

async def encode_frames(camera_id):
    out, file_path = camera_recordings[camera_id]

    while True:
        frame = await frame_buffers[camera_id].get()
        if frame is None:
            break

        try:
            out.write(frame)
        except Exception as e:
            print(f"Encoding error: {e}")

    # Release the video writer
    try:
        out.release()
    except Exception as e:
        print(f"Error releasing video writer: {e}")


def finalize_recording(camera_id):
    if camera_id in camera_recordings:
        out, file_path = camera_recordings.pop(camera_id)
        frame_buffers[camera_id].put_nowait(None)  # Signal encoding task to stop
        return file_path
    return None

def initialize_camera_recording(camera_id, frame_width, frame_height):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(RECORDINGS_DIR, f"{camera_id}_{timestamp}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(file_path, fourcc, FPS, (frame_width, frame_height))

    camera_recordings[camera_id] = (out, file_path)
    frame_buffers[camera_id] = asyncio.Queue(maxsize=BUFFER_LIMIT)

    asyncio.create_task(encode_frames(camera_id))
