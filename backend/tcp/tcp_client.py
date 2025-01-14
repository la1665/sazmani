import base64
import cv2
import datetime
import numpy as np
import os
import json
import uuid
import hmac
import hashlib
import asyncio
from pathlib import Path
from collections import deque
from twisted.internet import protocol
from twisted.protocols import basic
from sqlalchemy.future import select
from concurrent.futures import ThreadPoolExecutor

from settings import settings
from database.engine import async_session
from socket_management import emit_to_requested_sids
from crud.traffic import TrafficOperation
from schema.traffic import TrafficCreate
from models.record import DBRecord
from models.lpr import DBLpr



BASE_UPLOAD_DIR = Path("uploads")
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists


async def fetch_lpr_settings(lpr_id: int):
    """Fetch LPR settings from the database."""
    async with async_session() as session:
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

class SimpleTCPClient(basic.LineReceiver):
    delimiter = b'SSENDSS'  # Use <END> as the delimiter
    maxLength = 500 * 1024 * 1024
    def __init__(self):
        self.auth_message_id = None
        self.incomplete_data = ""
        self.authenticated = False  # Track authentication status locally
        self.message_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.batch_queue = asyncio.Queue()
        self.batch_size = 10
        self.batch_processing_interval = 5
        self.buffer = b""
        self.expected_length = None
        self.video_writer = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.frame_buffer = deque(maxlen=30)
        asyncio.create_task(self.process_batch_queue())

    def connectionMade(self):
        """Called when a connection to the server is made."""
        print(f"[INFO] Connected to {self.transport.getPeer()}")
        self.authenticate()
        # Start processing the message queue
        asyncio.create_task(self.process_message_queue())

    def authenticate(self):
        """Sends an authentication message with a secure token."""
        self.auth_message_id = str(uuid.uuid4())
        auth_message = self._create_auth_message(self.auth_message_id, self.factory.auth_token)
        self._send_message(auth_message)
        print(f"[INFO] Authentication message sent with ID: {self.auth_message_id}")

    def _create_auth_message(self, message_id, token):
        """Creates a JSON authentication message."""
        return json.dumps({
            "messageId": message_id,
            "messageType": "authentication",
            "messageBody": {"token": token}
        })

    def _send_message(self, message):
        """Sends a message to the server."""
        if self.transport and self.transport.connected:
            print(f"[INFO] Sending message: {message}")
            self.transport.write((message + '\n').encode('utf-8'))
        else:
            print("[ERROR] Transport is not connected. Message not sent.")

    def is_valid_utf8(self, data):
        try:
            data.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False

    def dataReceived(self, data):
        """Accumulates and processes data received from the server."""
        try:
            # Append the new data to the buffer
            self.incomplete_data += data.decode('utf-8')

            # Process all complete messages in the buffer
            while '<END>' in self.incomplete_data:
                full_message, self.incomplete_data = self.incomplete_data.split('<END>', 1)
                full_message = full_message.strip()  # Remove extra spaces or newlines (if any)

                if full_message:
                    try:
                        # Attempt to add the message to the queue
                        self.message_queue.put_nowait(full_message)
                    except asyncio.QueueFull:
                        # If the queue is full, remove the oldest message and add the new one
                        print("[WARN] Message queue is full. Dropping the oldest message.")
                        self.message_queue.get_nowait()  # Remove the oldest message
                        self.message_queue.put_nowait(full_message)  # Add the new message
        except UnicodeDecodeError as e:
            print(f"[ERROR] Failed to decode data: {e}")

    async def process_message_queue(self):
        while True:
            message = await self.message_queue.get()
            try:
                await self._process_message(message)
            except Exception as e:
                print(f"[ERROR] Exception in processing message: {e}")
            finally:
                self.message_queue.task_done()

    async def _process_message(self, message):
        """Processes each received message."""
        try:
            parsed_message = json.loads(message)
            message_type = parsed_message.get("messageType")
            handler = {
                "acknowledge": self._handle_acknowledgment,
                "command_response": self._handle_command_response,
                "plates_data": self._handle_plates_data,
                "live": self._handle_live_data,
                "heartbeat": self._handle_heartbeat,
                "resources": self._handle_resources,
                "recording": self._handle_recording,
                "camera_connection": self._handle_camera_connection
            }.get(message_type, self._handle_unknown_message)
            await handler(parsed_message)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse message: {e}")

    async def _fetch_and_send_lpr_settings(self):
        try:
            lpr_settings = await fetch_lpr_settings(self.factory.lpr_id)
            hmac_key = settings.HMAC_SECRET_KEY.encode()
            data_str = json.dumps(lpr_settings, separators=(",", ":"), sort_keys=True)
            hmac_signature = hmac.new(hmac_key, data_str.encode(), hashlib.sha256).hexdigest()

            settings_message = {
                "messageId": self.auth_message_id,
                "messageType": "lpr_settings",
                "messageBody": {
                    "data": lpr_settings,
                    "hmac": hmac_signature,
                },
            }
            self._send_message(json.dumps(settings_message))
            print("[INFO] LPR settings sent.")
        except Exception as e:
            print(f"[ERROR] Failed to send LPR settings: {e}")

    async def _handle_acknowledgment(self, message):
        reply_to = message["messageBody"].get("replyTo")
        if reply_to == self.auth_message_id:
            print("[INFO] Authentication successful.")
            self.authenticated = True
            self.factory.authenticated = True
            asyncio.create_task(self._fetch_and_send_lpr_settings())
        else:
            print(f"[INFO] Acknowledgment for unknown message ID: {reply_to}")

    async def _handle_recording(self, message):
        message_body = message["messageBody"]
        frame_base64 = message_body.get("frame")
        camera_id = message_body.get("camera_id")
        end_recording = message_body.get("end_recording")

        if end_recording:
            if self.video_writer:
                await self._write_batch_to_video()
                self.video_writer.release()
                title=os.path.basename(self.file_path)
                # Save the recording information to the database
                async with async_session() as session:
                    try:
                        record = DBRecord(
                            title=title,
                            camera_id=int(camera_id),
                            timestamp=datetime.datetime.now(),
                            video_url=f"uploads/recordings/{title}"
                        )
                        session.add(record)
                        await session.commit()

                        print(f"---------->> Recording saved: {self.file_path}")
                    except Exception as error:
                        await session.rollback()
                        print(f"[ERROR] Failed to save recording: {error}")

                self.video_writer = None
            else:
                print("No active recording to end.")
            return

        if not frame_base64 or not camera_id:
            print("Invalid message body")
            return

        # Decode the base64 frame
        try:
            frame_data = base64.b64decode(frame_base64)
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"Failed to decode frame: {e}")
            return

        # Initialize video writer if not already done
        if self.video_writer is None:
            try:
                # Generate filename based on camera name and timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{camera_id}_{timestamp}.mp4"

                # Ensure directory exists
                self.file_path = str(RECORDINGS_DIR / filename)

                frame_height, frame_width, _ = frame.shape
                fps = 10  # Adjust FPS as needed

                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(self.file_path, fourcc, fps, (frame_width, frame_height))

                if not self.video_writer.isOpened():
                    print("Failed to open video writer")
                    self.video_writer = None
                    return
            except Exception as error:
                print(f"[ERROR] Failed to initialize video writer: {error}")

        self.frame_buffer.append(frame)
        # Write the batch if the buffer is full
        if len(self.frame_buffer) >= self.batch_size:
            await self._write_batch_to_video()

    async def _write_batch_to_video(self):
        """Writes a batch of frames to the video file."""
        if not self.video_writer or not self.frame_buffer:
            return
        frames = list(self.frame_buffer)
        self.frame_buffer.clear()  # Clear the buffer after collecting frames
        # Offload the batch writing to a separate thread
        await asyncio.get_event_loop().run_in_executor(self.executor, lambda: [self.video_writer.write(frame) for frame in frames])


    async def _broadcast_to_socketio(self, event_name, data, camera_id=None):
        """Efficiently broadcast a message to all subscribed clients for an event."""
        await emit_to_requested_sids(event_name, data, camera_id)

    async def process_batch_queue(self):
        """Processes the batch queue periodically."""
        while True:
            try:
                batch = []
                for _ in range(self.batch_size):
                    item = await self.batch_queue.get()
                    batch.append(item)
                    self.batch_queue.task_done()

                if batch:
                    async with async_session() as session:
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
                print(f"[ERROR] Batch processing error: {e}")

            # Wait for the next processing interval
            await asyncio.sleep(self.batch_processing_interval)


    async def _handle_plates_data(self, message):
        # print("Plate data recived")
        message_body = message["messageBody"]
        camera_id = message_body.get("camera_id")
        timestamp = message_body.get("timestamp")
        cars = message_body.get("cars", [])

        # save_plates_data_to_db.delay(camera_id, timestamp, cars)
        try:
            for car in cars:
                plate_number = car.get("plate", {}).get("plate", "Unknown")
                ocr_accuracy = car.get("ocr_accuracy", "Unknown")
                vision_speed = car.get("vision_speed", 0.0)
                plate_image_base64 = car.get("plate", {}).get("plate_image", "")

                # Create a TrafficCreate object
                traffic_data = TrafficCreate(
                    plate_number=plate_number,
                    ocr_accuracy=ocr_accuracy,
                    vision_speed=vision_speed,
                    plate_image_path=plate_image_base64,
                    timestamp=timestamp,
                    camera_id=camera_id,
                )

                # Enqueue the traffic data for batch processing
                await self.batch_queue.put(traffic_data)
            print(f"[INFO] Enqueued {len(cars)} traffic records for batch processing.")
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
        # print(f"sending to socket ... {socketio_message['camera_id']}")
        asyncio.ensure_future(self._broadcast_to_socketio("plates_data", socketio_message, camera_id))


    async def _handle_command_response(self, message):
        """
        Handles the command response from the server.
        """
        pass

    async def _handle_live_data(self, message):
        message_body = message["messageBody"]
        camera_id = message_body.get("camera_id")
        live_data = {
            "messageType": "live",
            "live_image": message_body.get("live_image"),
            "camera_id": camera_id
        }

        print(f"sending live to socket ... {live_data['camera_id']}")
        asyncio.ensure_future(self._broadcast_to_socketio("live", live_data, camera_id))

    async  def _handle_unknown_message(self, message):
        print(f"[WARN] Received unknown message type: {message.get('messageType')}")

    def send_command(self, command_data):
        if self.authenticated:
            command_message = self._create_command_message(command_data)
            self._send_message(command_message)
        else:
            print("[ERROR] Cannot send command: client is not authenticated.")

    def _create_command_message(self, command_data):
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
        })

    async def _handle_resources(self, message):
        print(f"[INFO] Resources received: {message['messageBody']}")
        # Process resource data here (e.g., log it or trigger some actions)
        message["messageBody"]["lpr_id"] = self.factory.lpr_id
        asyncio.ensure_future(self._broadcast_to_socketio("resources", message['messageBody']))

    async def _handle_camera_connection(self, message):
        print(f"[INFO] Camera connection status: {message['messageBody']}")
        is_connected = message["messageBody"].get("Connection")
        lpr_id = self.factory.lpr_id
        # Process camera connection status here (e.g., log or update UI)
        try:
            # Broadcast the heartbeat message to all subscribed clients
            await self._broadcast_to_socketio(event_name="camera_connection", data={
                "camera_connection": is_connected,
                "lpr_id": lpr_id,
            })

            # Optional: Add additional logic for handling heartbeat data, if necessary
        except Exception as e:
            print(f"[ERROR] Failed to handle camera connection message: {e}")


    def connectionLost(self, reason):
        print(f"[INFO] Connection lost: {reason}")
        self.factory.clientConnectionLost(self.transport.connector, reason)

    async def _handle_heartbeat(self, message):
        """
        Handles heartbeat messages and sends them to subscribed clients via the socket.
        """
        try:
            # Log the received heartbeat message (optional)
            print(f"[INFO] Heartbeat received: {message}")
            message["lpr_id"] = self.factory.lpr_id

            # Broadcast the heartbeat message to all subscribed clients
            await self._broadcast_to_socketio(event_name="heartbeat", data=message)

            # Optional: Add additional logic for handling heartbeat data, if necessary
        except Exception as e:
            print(f"[ERROR] Failed to handle heartbeat message: {e}")

from twisted.internet import reactor, ssl

class ReconnectingTCPClientFactory(protocol.ReconnectingClientFactory):
    def __init__(self, lpr_id, server_ip, port, auth_token):
        self.lpr_id = lpr_id
        self.auth_token = auth_token
        self.authenticated = False
        self.active_protocol = None  # Track the active protocol instance
        self.server_ip = server_ip
        self.port = port
        self.reconnecting = False  # Flag to manage reconnections
        self.connection_in_progress = False  # Prevent overlapping connection attempts

    def buildProtocol(self, addr):
        # Always create a new protocol but manage its lifecycle
        print(f"[INFO] Connected to {addr}")
        self.resetDelay()  # Reset reconnection delay on successful connection
        self.reconnecting = False  # Clear reconnecting flag
        self.connection_in_progress = False  # Clear connection-in-progress flag
        client = SimpleTCPClient()
        client.factory = self
        self.active_protocol = client  # Set the active protocol instance
        return client

    def clientConnectionLost(self, connector, reason):
        print(f"[INFO] Connection lost: {reason}. Scheduling reconnect.")
        self.active_protocol = None  # Clear the active protocol on disconnect
        if not self.connection_in_progress:
            self._attempt_reconnect()  # Only attempt reconnect if not already in progress

    def clientConnectionFailed(self, connector, reason):
        print(f"[ERROR] Connection failed: {reason}. Scheduling reconnect.")
        self.active_protocol = None  # Clear the active protocol on failure
        if not self.connection_in_progress:
            self._attempt_reconnect()  # Only attempt reconnect if not already in progress

    def _attempt_reconnect(self):
        """Reconnect with a fixed interval and ensure single connection attempt."""
        if self.connection_in_progress:
            print("[DEBUG] Connection already in progress. Skipping reconnect.")
            return

        if self.active_protocol is not None:
            print("[DEBUG] Client is already connected. No need to reconnect.")
            return

        self.connection_in_progress = True  # Mark connection as in progress
        print(f"[INFO] Attempting to reconnect to {self.server_ip}:{self.port}...")

        # Create SSL context for secure connection
        class ClientContextFactory(ssl.ClientContextFactory):
            def getContext(self):
                context = ssl.SSL.Context(ssl.SSL.TLSv1_2_METHOD)
                # Resolve absolute paths for the certificates
                client_key_path = Path(settings.CLIENT_KEY_PATH).resolve()
                client_cert_path = Path(settings.CLIENT_CERT_PATH).resolve()
                ca_cert_path = Path(settings.CA_CERT_PATH).resolve()

                # Log paths for debugging
                print(f"Using client key: {client_key_path}")
                print(f"Using client cert: {client_cert_path}")
                print(f"Using CA cert: {ca_cert_path}")

                # Use the certificates in the SSL context
                context.use_certificate_file(str(client_cert_path))
                context.use_privatekey_file(str(client_key_path))
                context.load_verify_locations(str(ca_cert_path))


                context.set_verify(ssl.SSL.VERIFY_PEER, lambda conn, cert, errno, depth, ok: ok)
                return context

        try:
            reactor.connectSSL(self.server_ip, self.port, self, ClientContextFactory())
        except Exception as e:
            print(f"[ERROR] Reconnection failed: {e}")
        finally:
            # Schedule the next reconnect attempt after 60 seconds
            reactor.callLater(5, self._reset_connection_state_and_retry)

    def _reset_connection_state_and_retry(self):
        if self.active_protocol is not None:
            print("[INFO] Client is already connected. Skipping retry.")
            return
        self.connection_in_progress = False  # Allow new connection attempt
        print("[INFO] Retrying connection...")
        self._attempt_reconnect()


def send_command_to_server(factory, command_data):
    if factory.authenticated and factory.active_protocol:
        print(f"[INFO] Sending command to server: {command_data}")
        factory.active_protocol.send_command(command_data)
    else:
        print("[ERROR] Cannot send command: Client is not authenticated or connected.")
