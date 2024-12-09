import os
import json
import uuid
import hmac
import hashlib
import asyncio
from pathlib import Path
from twisted.internet import protocol
from twisted.protocols import basic
from sqlalchemy.exc import SQLAlchemyError


from settings import settings
from database.engine import async_session
from socket_management import emit_to_requested_sids
from crud.traffic import TrafficOperation
from schema.traffic import TrafficCreate


async def fetch_lpr_settings(lpr_id: int):
    from sqlalchemy.future import select
    from models.lpr import DBLpr

    async with async_session() as session:
        query = await session.execute(select(DBLpr).where(DBLpr.id == lpr_id))
        lpr = query.scalar_one_or_none()
        if not lpr:
            raise ValueError(f"LPR with ID {lpr_id} not found.")
        # Prepare data for cameras and their settings
        cameras_data = []
        for camera in lpr.cameras:
            camera_data = {
                "camera_id": camera.id,
                "settings": []
            }
            for setting in camera.settings:
                if setting.setting_type.value == "int":
                    value = int(setting.value)
                elif setting.setting_type.value == "float":
                    value = float(setting.value)
                elif setting.setting_type.value == "string":
                    value = str(setting.value)
                else:
                    value = setting.value
                setting_data = {
                    "name": setting.name,
                    "value": value
                }
                camera_data["settings"].append(setting_data)
            cameras_data.append(camera_data)

        settings_data = []
        for setting in lpr.settings:
            if setting.setting_type.value == "int":
                value = int(setting.value)
            elif setting.setting_type.value == "float":
                value = float(setting.value)
            elif setting.setting_type.value == "string":
                value = str(setting.value)
            else:
                value = setting.value
            setting_data = {
                "name": setting.name,
                "value": value
            }
            settings_data.append(setting_data)

        return {"lpr_id": lpr.id, "settings": settings_data, "cameras_data": cameras_data}


class SimpleTCPClient(basic.LineReceiver):
    delimiter = b'SSENDSS'  # Use <END> as the delimiter
    maxLength = 500 * 1024 * 1024
    def __init__(self):
        self.auth_message_id = None
        self.incomplete_data = ""
        self.authenticated = False  # Track authentication status locally
        self.message_queue = asyncio.Queue()
        self.lock = asyncio.Lock()

        self.buffer = b""
        self.expected_length = None

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
                    # Enqueue the complete message for asynchronous processing
                    asyncio.create_task(self.message_queue.put(full_message))
        except UnicodeDecodeError as e:
            print(f"[ERROR] Failed to decode data: {e}")


    async def process_message_queue(self):
        """Asynchronously processes messages from the queue."""
        try:
            while True:
                try:
                    message = await self.message_queue.get()
                    await self._process_message(message)
                except Exception as e:
                    print(f"[ERROR] Exception in processing message: {e}")
                finally:
                    if not self.message_queue.empty():
                        self.message_queue.task_done()
        except asyncio.CancelledError:
            print("[INFO] Message processing task cancelled. Cleaning up...")

            # Ensure no unprocessed items are left in the queue
            while not self.message_queue.empty():
                self.message_queue.get_nowait()
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
                "camera_connection": self._handle_camera_connection
            }.get(message_type, self._handle_unknown_message)
            await handler(parsed_message)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse message: {e}")

    async def _handle_acknowledgment(self, message):
        reply_to = message["messageBody"].get("replyTo")
        if reply_to == self.auth_message_id:
            print("[INFO] Authentication successful.")
            self.authenticated = True
            self.factory.authenticated = True

            # Fetch and send LPR settings
            try:
                # Assuming LPR ID is passed in the factory or another way
                lpr_settings = await fetch_lpr_settings(self.factory.lpr_id)
                hmac_key = settings.HMAC_SECRET_KEY.encode()
                data_str = json.dumps(lpr_settings, separators=(',', ':'), sort_keys=True)
                hmac_signature = hmac.new(hmac_key, data_str.encode(), hashlib.sha256).hexdigest()
                settings_message = {
                    "messageId": self.auth_message_id,
                    "messageType": "lpr_settings",
                    "messageBody":
                        {
                            "data": lpr_settings,
                            "hmac": hmac_signature
                        }
                }
                self._send_message(json.dumps(settings_message))
                print("[INFO] LPR settings sent to the server.")
            except Exception as e:
                print(f"[ERROR] Failed to send LPR settings: {e}")

        else:
            print(f"[INFO] Received acknowledgment for message ID: {reply_to}")

    async def _broadcast_to_socketio(self, event_name, data, camera_id):
        """Efficiently broadcast a message to all subscribed clients for an event."""
        await emit_to_requested_sids(event_name, data, camera_id)

    async def _handle_plates_data(self, message):
        # print("Plate data recived")
        message_body = message["messageBody"]
        camera_id = message_body.get("camera_id")
        timestamp = message_body.get("timestamp")


        try:
            async with async_session() as session:
                traffic_operation = TrafficOperation(session)

                # Retrieve the camera object to validate and find the associated gate
                # camera_query = await session.execute(
                #     select(DBCamera).where(DBCamera.id == camera_id)
                # )
                # db_camera = camera_query.scalar_one_or_none()

                # if not db_camera or not db_camera.gate_id:
                #     print(f"[ERROR] Camera with ID {camera_id} not found or has no associated gate.")
                #     return  # Handle missing camera or gate appropriately

                # gate_id = db_camera.gate_id

                # Process each car in the received message
            try:
                for car in message_body.get("cars", []):
                    plate_number = car.get("plate", {}).get("plate", "Unknown")
                    ocr_accuracy = car.get("ocr_accuracy", "Unknown")
                    vision_speed = car.get("vision_speed", 0.0)
                    # Create a TrafficCreate object for the car
                    traffic_data = TrafficCreate(
                        plate_number=plate_number,
                        ocr_accuracy=ocr_accuracy,
                        vision_speed=vision_speed,
                        timestamp=timestamp,
                        camera_id=camera_id
                    )

                    # Use the TrafficOperation to store the traffic data
                    traffic_entry = await traffic_operation.create_traffic(traffic_data)
                    print(f"[INFO] Stored traffic data: {traffic_entry.id} for plate {plate_number}")

            except SQLAlchemyError as e:
                print(f"[ERROR] Database error while storing traffic data: {e}")
                await session.rollback()
            finally:
                await session.close()

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")

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
        cpu_usage = message["messageBody"].get("CPU_USAGE")
        ram_usage = message["messageBody"].get("RAM_USAGE")
        free_space_percentage = message["messageBody"].get("Free_Space_Percentage")
        # Process resource data here (e.g., log it or trigger some actions)

    async def _handle_camera_connection(self, message):
        print(f"[INFO] Camera connection status: {message['messageBody']}")
        is_connected = message["messageBody"].get("Connection")
        # Process camera connection status here (e.g., log or update UI)


    def connectionLost(self, reason):
        print(f"[INFO] Connection lost: {reason}")
        self.factory.clientConnectionLost(self.transport.connector, reason)

    async def _handle_heartbeat(self, message):
        print(message)

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


                # client_key_path = os.path.abspath(settings.CLIENT_KEY_PATH)
                # client_cert_path = os.path.abspath(settings.CLIENT_CERT_PATH)
                # ca_cert_path = os.path.abspath(settings.CA_CERT_PATH)

                # Verify the paths
                # print(f"Using client key: {client_key_path}")
                # print(f"Using client cert: {client_cert_path}")
                # print(f"Using CA cert: {ca_cert_path}")
                # Use the certificates in the context
                # context.use_certificate_file(client_cert_path)
                # context.use_privatekey_file(client_key_path)
                # context.load_verify_locations(ca_cert_path)
                # context.use_certificate_file("client.crt")
                # context.use_privatekey_file("client.key")
                # context.load_verify_locations("ca.crt")

                # context.use_certificate_file(settings.CLIENT_CERT_PATH)
                # context.use_privatekey_file(settings.CLIENT_KEY_PATH)
                # context.load_verify_locations(settings.CA_CERT_PATH)
                context.set_verify(ssl.SSL.VERIFY_PEER, lambda conn, cert, errno, depth, ok: ok)
                return context

        try:
            reactor.connectSSL(self.server_ip, self.port, self, ClientContextFactory())
        except Exception as e:
            print(f"[ERROR] Reconnection failed: {e}")
        finally:
            # Schedule the next reconnect attempt after 60 seconds
            reactor.callLater(60, self._reset_connection_state_and_retry)

    def _reset_connection_state_and_retry(self):
        if self.active_protocol is not None:
            print("[INFO] Client is already connected. Skipping retry.")
            return
        self.connection_in_progress = False  # Allow new connection attempt
        print("[INFO] Retrying connection...")
        self._attempt_reconnect()






# def connect_to_server(server_ip, port, auth_token):
#     factory = ReconnectingTCPClientFactory(server_ip, port, auth_token)
#     factory._attempt_reconnect()  # Start initial connection attempt
#     return factory



def send_command_to_server(factory, command_data):
    if factory.authenticated and factory.active_protocol:
        print(f"[INFO] Sending command to server: {command_data}")
        factory.active_protocol.send_command(command_data)
    else:
        print("[ERROR] Cannot send command: Client is not authenticated or connected.")

# def graceful_shutdown(signal, frame):
#     print("Shutting down gracefully...")
#     reactor.stop()


# def start_reactor():
#     reactor.run()


# if __name__ == "__main__":
#     server_ip = "185.81.99.23"
#     port = 45

#     # Connect to the server and start reactor
#     factory = connect_to_server(server_ip, port)
#     start_reactor()
