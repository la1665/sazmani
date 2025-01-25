# handlers.py
import re
import asyncio
import base64
import datetime
import hashlib
import json
import os
import uuid
import cv2
import numpy as np
from nats.aio.msg import Msg
from nats.aio.client import Client as NATS
import hmac
from pathlib import Path
from sqlalchemy.future import select


from settings import settings
# from database.engine import async_session
from database.engine import nats_session
from crud.traffic import TrafficOperation
from schema.traffic import TrafficCreate
from models.record import DBRecord
from models.lpr import DBLpr


# Get the root directory of the project
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Adjust to go up two levels to 'sazman_windows'
relative_upload_dir = settings.BASE_UPLOAD_DIR
# Define the uploads directory at the project root
# BASE_UPLOAD_DIR = PROJECT_ROOT / relative_upload_dir
BASE_UPLOAD_DIR = Path(relative_upload_dir)

# Ensure relative_upload_dir is not None
if not relative_upload_dir:
    raise ValueError("BASE_UPLOAD_DIR is not set in the environment or settings.")


# Create the required directories
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_UPLOAD_DIR = BASE_UPLOAD_DIR / "plate_images"
IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TRAFFIC_UPLOAD_DIR = BASE_UPLOAD_DIR / "traffic_images"
TRAFFIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



# CURRENT_DIR = Path(__file__).resolve().parent
# PROJECT_ROOT = CURRENT_DIR.parent
# relative_upload_dir = settings.BASE_UPLOAD_DIR

# BASE_UPLOAD_DIR = PROJECT_ROOT / relative_upload_dir

# RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
# RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# IMAGE_UPLOAD_DIR = BASE_UPLOAD_DIR/ "plate_images"
# IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


def save_image_opencv(byte_array, file_path):

    try:
        if isinstance(byte_array, list):
            byte_array = bytes(byte_array)
        nparr = np.frombuffer(byte_array, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        success = cv2.imwrite(file_path, image)
        if success:
            print(f"Image saved successfully to {file_path}")
        else:
            print(f"Failed to save image to {file_path}")
    except Exception as e:
        print(f"Failed to save image: {e}")

async def fetch_lpr_settings(lpr_id: int):
    """Fetch LPR settings from the database."""
    async with nats_session() as session:
        try:
            query = await session.execute(select(DBLpr).where(DBLpr.id == lpr_id))
            lpr = query.scalar_one_or_none()
            if not lpr:
                raise ValueError(f"LPR with ID {lpr_id} not found.")

            print(f"founded lpr is: {lpr.id}")
            return prepare_lpr_data(lpr)
        except Exception as e:
            print(f"[ERROR] Failed to fetch LPR settings: {e}")
            raise


def prepare_lpr_data(lpr):
    """Prepare LPR data for the message payload."""
    cameras_data = [
        {
            "camera_id": camera.id,
            "settings": [{"name": setting.name, "value": parse_setting_value(setting)} for setting in camera.settings],
        }
        for camera in lpr.cameras
    ]
    settings_data = [{"name": setting.name, "value": parse_setting_value(setting)} for setting in lpr.settings]
    print(settings_data)
    return {"lpr_id": lpr.id, "settings": settings_data, "cameras_data": cameras_data}

def parse_setting_value(setting):
    """Parse setting value based on its type."""
    if setting.setting_type.value == "int":
        return int(setting.value)
    elif setting.setting_type.value == "float":
        return float(setting.value)
    elif setting.setting_type.value == "string":
        return str(setting.value)
    return setting.value

async def handle_lpr_settings_request(msg: Msg, nc: NATS) -> None:
    """
    Handle incoming LPR settings requests.
    Expects a JSON payload with 'client_id'.
    """
    try:
        request = json.loads(msg.data.decode())

        client_id = int(request.get("client_id"))

        lpr_settings = await fetch_lpr_settings(client_id)
        hmac_key = settings.HMAC_SECRET_KEY.encode()
        data_str = json.dumps(lpr_settings, separators=(",", ":"), sort_keys=True)
        hmac_signature = hmac.new(hmac_key, data_str.encode(), hashlib.sha256).hexdigest()

        response_subject = f"alpr.settings.response.{client_id}"

        response_data = json.dumps({
            "messageId":  str(uuid.uuid4()),
            "messageType": "lpr_settings",
            "messageBody": {
                "data": lpr_settings,
                "hmac": hmac_signature,
            }
        })

        print(f"Publishing response to {response_subject}: {response_data}")
        await nc.publish(response_subject, response_data.encode())

    except Exception as e:
       print(f"Exception in handling LPR settings request: {e}")


async def send_command_to_client(nc: NATS, client_id: str, command_data: dict) -> None:
    """
    Send a command to a specific client and listen for a response.
    """
    command_message = {
        "messageType": "command",
        "messageBody": {
            "data": command_data,
        }
    }

    command_topic = f"command.{client_id}"
    await nc.publish(command_topic, json.dumps(command_message).encode())
    print(f"Command sent to {command_topic}: {command_message}")

    response_topic = f"response.{client_id}"

    async def handle_response(msg: Msg):
        response = json.loads(msg.data.decode())
        print(f"Received response from {response_topic}: {response}")

    # Subscribe to the response topic
    await nc.subscribe(response_topic, cb=handle_response)


async def handle_socket_plate(message, emit_to_requested_sids):
    try:
        # Log the received heartbeat message (optional)
        print(f"[INFO] plate received: ")
        # Broadcast the heartbeat message to all subscribed clients
        await emit_to_requested_sids(event_name="plates_data", data=message)
        # Optional: Add additional logic for handling heartbeat data, if necessary
    except Exception as e:
        print(f"[ERROR] Failed to handle heartbeat message: {e}")


async def handle_message(msg, emit_to_requested_sids) -> None:
    """
    Handles all incoming messages on the subject pattern 'messages.*'.
    Dispatches to specific handlers based on 'messageType'.
    """
    try:
        message = json.loads(msg.data.decode())
        message_type = message.get("messageType")

        if message_type == "live":
            await handle_live_data(message, emit_to_requested_sids)
        elif message_type == "resources":
            await handle_resources(message, emit_to_requested_sids)
        elif message_type == "camera_connection":
            await handle_camera_connection(message, emit_to_requested_sids)
        elif message_type == "heartbeat":
            await handle_heartbeat(message, emit_to_requested_sids)
        elif message_type=="plates_data":
            await handle_socket_plate(message, emit_to_requested_sids)
        else:
            print(f"Unknown message type: {message_type}")

    except json.JSONDecodeError as e:
        print(f"Failed to decode message: {e}")
    except Exception as e:
        print(f"Unexpected error in handle_message: {e}")


async def handle_live_data(message: dict, emit_to_requested_sids) -> None:
    message_body = message["messageBody"]
    camera_id = message_body.get("camera_id")
    live_data = {
        "messageType": "live",
        "live_image": message_body.get("live_image"),
        "camera_id": camera_id
    }

    print(f"sending live to socket ... {live_data['camera_id']}")

    await emit_to_requested_sids("live", live_data)


async def handle_resources(message: dict, emit_to_requested_sids) -> None:
    """Handle resource status messages."""
    print(f"Resources received: {message}")
    await emit_to_requested_sids("resources", message['messageBody'])


import imageio_ffmpeg as ffmpeg
from collections import deque
from concurrent.futures import ThreadPoolExecutor

io_executor = ThreadPoolExecutor(max_workers=2)
BUFFER_LIMIT = 30
FPS = 10
FFMPEG_PARAMS = ["-preset", "ultrafast"]

# Global recording states
camera_recordings = {}
frame_buffers = {}




async def handle_recording(msg):
    try:
        message = json.loads(msg.data.decode())
    except Exception as exp:
        print(f"Extract recording message exception: {exp}")
        return

    message_body = message.get("messageBody", {})
    frame_bytes = message_body.get("frame")
    camera_id = message_body.get("camera_id")
    end_recording = message_body.get("end_recording")

    if not frame_bytes and not end_recording:
        print("Invalid message body")
        return

    if end_recording:
        def finalize_recording(camera_id):
            if camera_id in camera_recordings:
                writer, file_path = camera_recordings.pop(camera_id)
                writer.close()
                return file_path
            return None

        file_path = finalize_recording(camera_id)
        if file_path:
            title = os.path.basename(file_path)
            asyncio.create_task(save_recording_metadata(title, camera_id, file_path))
        return

    try:
        if isinstance(frame_bytes, list):
            frame_bytes = bytes(frame_bytes)
        frame = await asyncio.to_thread(cv2.imdecode, np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Decoded frame is None")
    except Exception as e:
        print(f"Failed to decode frame: {e}")
        return

    if camera_id not in camera_recordings:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(RECORDINGS_DIR, f"{camera_id}_{timestamp}.mp4")
        writer = ffmpeg.write_frames(
            file_path,
            size=(frame.shape[1], frame.shape[0]),
            fps=FPS,
            codec="libx264",
            pix_fmt_in="rgb24",
            output_params=["-preset", "ultrafast", "-crf", "28"]
        )
        writer.send(None)
        camera_recordings[camera_id] = (writer, file_path)
        frame_buffers[camera_id] = asyncio.Queue(maxsize=BUFFER_LIMIT)

    try:
        await frame_buffers[camera_id].put(frame.tobytes())
        writer, file_path = camera_recordings[camera_id]
        while not frame_buffers[camera_id].empty():
            buffered_frame = await frame_buffers[camera_id].get()
            await asyncio.to_thread(writer.send, buffered_frame)
    except Exception as e:
        print(f"Error handling frame: {e}")


async def handle_camera_connection(message: dict, emit_to_requested_sids) -> None:
    """Handle camera connection status messages."""
    print(f"Camera connection status: {message}")
    print(f"[INFO] Camera connection status: {message['messageBody']}")
    is_connected = message["messageBody"].get("Connection")
    lpr_id = message["lpr_id"]
    # Process camera connection status here (e.g., log or update UI)
    try:
        # Broadcast the heartbeat message to all subscribed clients
        await emit_to_requested_sids(event_name="camera_connection", data={
            "camera_connection": is_connected,
            "lpr_id": lpr_id,
        })

        # Optional: Add additional logic for handling heartbeat data, if necessary
    except Exception as e:
        print(f"[ERROR] Failed to handle camera connection message: {e}")


async def handle_heartbeat(message: dict, emit_to_requested_sids) -> None:
    try:
        # Log the received heartbeat message (optional)
        print(f"[INFO] Heartbeat received: {message}")
        # Broadcast the heartbeat message to all subscribed clients
        await emit_to_requested_sids(event_name="heartbeat", data=message)

        # Optional: Add additional logic for handling heartbeat data, if necessary
    except Exception as e:
        print(f"[ERROR] Failed to handle heartbeat message: {e}")


async def handle_plates_data(msg: Msg, nats_client: NATS) -> None:
    """
    Handle plates_data messages from JetStream.
    Acknowledge the message after processing.
    """
    try:
        message = json.loads(msg.data.decode())
        await msg.ack()
        print("JetStream plates_data received and processed.")



        message_body = message["messageBody"]
        camera_id = message_body.get("camera_id")
        timestamp = message_body.get("timestamp")
        full_image_array = message_body.get("full_image")
        cars = message_body.get("cars", [])
        #timestamp_dt = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H-%M-%S")

        # save_plates_data_to_db.delay(camera_id, timestamp, cars)
        try:
            batch = []
            for car in cars:
                plate_number = car.get("plate", {}).get("plate", "Unknown")
                ocr_accuracy = car.get("ocr_accuracy", "Unknown")
                vision_speed = car.get("vision_speed", 0.0)
                plate_image_array = car.get("plate", {}).get("plate_image", "")

                full_image_name = f"{plate_number}_{uuid.uuid4()}.jpg"
                full_image_path = get_image_path(camera_id, datetime.datetime.now(), full_image_name, TRAFFIC_UPLOAD_DIR)
                save_image_opencv(full_image_array, full_image_path)
                plate_image_name = f"{plate_number}_{uuid.uuid4()}.jpg"
                plate_image_path = get_image_path(camera_id, datetime.datetime.now(), plate_image_name, IMAGE_UPLOAD_DIR)
                save_image_opencv(plate_image_array, plate_image_path)

                # Split the plate_number into components
                match = re.match(r"(\d{2})([a-zA-Z])(\d{3})(\d{2})", plate_number)
                if not match:
                    print(f"[WARNING] Invalid plate number format: {plate_number}")
                    continue

                prefix_2, alpha, mid_3, suffix_2 = match.groups()

                # Create a TrafficCreate object
                traffic_data = TrafficCreate(
                    prefix_2=prefix_2,
                    alpha=alpha,
                    mid_3=mid_3,
                    suffix_2=suffix_2,
                    plate_number=plate_number,
                    ocr_accuracy=ocr_accuracy,
                    vision_speed=vision_speed,
                    plate_image_path=str(plate_image_path),
                    full_image_path=str(full_image_path),
                    timestamp=timestamp,
                    camera_id=camera_id,
                )

                # Enqueue the traffic data for batch processing
                batch.append(traffic_data)
            print(f"[INFO] Enqueued {len(cars)} traffic records for batch processing.")
            if batch:
                async with nats_session() as session:
                    traffic_operation = TrafficOperation(session)
                    try:
                        for traffic_data in batch:
                            await traffic_operation.create_traffic(traffic_data)
                        await session.commit()
                        print(f"[INFO] Successfully stored {len(batch)} traffic records.")
                    except Exception as e:
                        await session.rollback()
                        print(f"[ERROR] Failed to store traffic records in batch: {e}")
                    finally:
                        await session.close()
        except Exception as e:
            print(f"[ERROR] Failed to handle plates data: {e}")

        socketio_message = {
            "messageType": "plates_data",
            "timestamp": timestamp,
            "camera_id": camera_id,
            "full_image": message_body.get("full_image"),
            "cars": [
                {
                    "plate_number": car.get("plate", {}).get("plate", "Unknown"),
                    "plate_image": car.get("plate", {}).get("plate_image", ""),
                    "ocr_accuracy": car.get("ocr_accuracy", "Unknown"),
                    "vision_speed": car.get("vision_speed", 0.0),
                    "vehicle_class": car.get("vehicle_class", {}),
                    "vehicle_type": car.get("vehicle_type", {}),
                    "vehicle_color": car.get("vehicle_color", {})
                }
                for car in message_body.get("cars", [])
            ]
        }

        try:
            subject = "socketio.plates_data"  # NATS subject for socket.io messages
            await nats_client.publish(subject, json.dumps(socketio_message).encode())
            print(f"[INFO] Published socketio_message to NATS subject '{subject}'.")
        except Exception as e:
            print(f"[ERROR] Failed to publish socketio_message to NATS: {e}")


    except Exception as e:
        print(f"Failed to handle plates_data: {e}")


def _create_command_message(command_data):
    """Creates and signs a command message with HMAC for integrity."""
    hmac_key = settings.HMAC_SECRET_KEY.encode()
    data_str = json.dumps(command_data, separators=(',', ':'), sort_keys=True)
    hmac_signature = hmac.new(hmac_key, data_str.encode(), hashlib.sha256).hexdigest()
    return json.dumps({
        "messageId": str(uuid.uuid4()),
        "messageType": "command",
        "messageBody": {
            "data": command_data,
            "hmac": hmac_signature
        }
    }).encode()

def get_image_path(camera_id: int, timestamp: datetime, image_name: str, upload_dir) -> Path:

    year = timestamp.year
    month = f"{timestamp.month:02d}"  # Zero-padded month
    day = f"{timestamp.day:02d}"      # Zero-padded day

    # Create the directory path
    dir_path = upload_dir / str(camera_id) / str(year) / month / day
    dir_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    return dir_path / image_name
