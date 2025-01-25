import os
from jose import jwt, JWTError
import asyncio
import time
import logging
from nats.errors import OutboundBufferLimitError
from nats.aio.client import Client as NATS
from socketio import AsyncServer
from datetime import datetime, timezone
from heapq import heappush, heappop
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from settings import settings
# from database.engine import async_session
from database.engine import nats_session
from models.user import DBUser, UserType
from models.camera import DBCamera
from shared_resources import connections
from nats_consumer.nats_setup import create_ssl_context, connect_to_nats_server
from nats_consumer.handlers import _create_command_message, handle_message

logger = logging.getLogger(__name__)

nats_client = NATS()

async def connect_to_nats():
    ssl_ctx = await create_ssl_context(
        settings.NATS_CA_PATH,
        settings.NATS_CERT_PATH,
        settings.NATS_KEY_PATH
    )

    # Connect to NATS
    global nats_client
    nats_client = await connect_to_nats_server(ssl_ctx)

    async def on_message(msg):
        # Pass the message to the handler
        await handle_message(msg, emit_to_requested_sids)

    await nats_client.subscribe("socketio.*", cb=on_message)
    print("Subscribed to 'authenticate' subject.")


sio = AsyncServer(
    async_mode="asgi",  # Use ASGI mode for FastAPI compatibility
    cors_allowed_origins="*",  # Allow all origins for CORS; adjust as needed
    logger=True,
    engineio_logger=True,
)

worker_running = True  # Controls the expiration handling
# No message_queue or message_worker needed
class SessionManager:
    def __init__(self):
        self.session_tokens = {}
        self.sid_role_map = {}
        self.token_expirations = []
        self.data_lock = asyncio.Lock()

    async def add_session(self, sid, token, user=None, expiration=None):
        async with self.data_lock:
            self.session_tokens[sid] = token
            self.sid_role_map[sid] = user
            if not expiration is None:
                heappush(self.token_expirations, (expiration.timestamp(), sid))

    async def remove_session(self, sid):
        async with self.data_lock:
            self.session_tokens.pop(sid, None)
            self.sid_role_map.pop(sid, None)

    async def update_token(self, sid, token, expiration):
        async with self.data_lock:
            self.session_tokens[sid] = token
            if not expiration is None:
                heappush(self.token_expirations, (expiration.timestamp(), sid))

    async def is_token_valid(self, sid):
        async with self.data_lock:
            return sid in self.session_tokens

    async def handle_expirations(self):
        while worker_running:
            async with self.data_lock:
                if not self.token_expirations:
                    next_wait = 60
                else:
                    now_ts = datetime.now(timezone.utc).timestamp()
                    next_exp, _ = self.token_expirations[0]
                    next_wait = max(0, next_exp - now_ts)

            try:
                await asyncio.sleep(next_wait)
            except asyncio.CancelledError:
                continue  # token updated, re-check

            expired_sids = []
            async with self.data_lock:
                now_ts = datetime.now(timezone.utc).timestamp()
                while self.token_expirations and self.token_expirations[0][0] < now_ts:
                    _, expired_sid = heappop(self.token_expirations)
                    if expired_sid in self.session_tokens:
                        expired_sids.append(expired_sid)

            # Disconnect expired sessions outside the lock
            for sid in expired_sids:
                if sio.manager.is_connected(sid):
                    logger.info(f"[INFO] Token expired for {sid}, disconnecting.")
                    await sio.disconnect(sid)

session_mgr = SessionManager()

async def validate_and_get_user(token: str):
    """Validates a JWT token and retrieves the user from the database."""
    try:
        if not settings.SECRET_KEY or not settings.ALGORITHM:
            raise ValueError("SECRET_KEY and ALGORITHM must be set in the settings.")

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        personal_number = payload.get("sub")
        if not personal_number:
            raise ValueError("Invalid token: Missing 'sub'")
        async with nats_session() as session:
            query = await session.execute(
                select(DBUser).where(DBUser.personal_number == personal_number)
            )
            user = query.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            return user
    except JWTError:
        raise ValueError("Invalid token")


@sio.event
async def connect(sid, environ):
    """
    Event triggered when a client connects to the WebSocket.
    """
    token = environ.get("HTTP_AUTHORIZATION")
    if not token:
        logger.error(f"Connection rejected for SID {sid}: Missing token")
        await sio.disconnect(sid)
        return

    try:
        # Validate and fetch user
        user = await validate_and_get_user(token.replace("Bearer ", ""))
        if user.user_type not in [UserType.ADMIN, UserType.STAFF, UserType.VIEWER]:
            logger.error(f"Unauthorized role for SID {sid}: {user.user_type}")
            await sio.disconnect(sid)
            return

        # Map SID to the user
        # sid_role_map[sid] = user
        await session_mgr.add_session(sid, token, user, None)
        logger.info(f"Client {sid} connected with role {user.user_type}")
        await sio.emit("connection_ack", {"message": "Connected"}, to=sid)

        #decoded_token = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
        #role = decoded_token.get("role", "viewer")
        #expiration = datetime.fromtimestamp(decoded_token['exp'], tz=timezone.utc)
        # await session_mgr.add_session(sid, auth_token, None, None)

        #logger.info(f"Connection accepted for role: {role} (SID: {sid})")
        return True
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        return False


# @sio.event
# async def refresh_token(sid, new_token):
#     try:
#         decoded_token = jwt.decode(new_token, SECRET_KEY, algorithms=["HS256"])
#         expiration = datetime.fromtimestamp(decoded_token['exp'], tz=timezone.utc)
#         await session_mgr.update_token(sid, new_token, expiration)
#         logger.info(f"[INFO] Token for session {sid} successfully updated.")
#     except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
#         logger.error(f"[ERROR] Invalid token for session {sid}. Disconnecting.")
#         await sio.emit('error', {'message': 'Invalid or expired token.'}, to=sid)
#         await sio.disconnect(sid)


@sio.event
async def disconnect(sid):
    await session_mgr.remove_session(sid)
    logger.info(f"Client {sid} disconnected")


@sio.event
async def subscribe(sid, data):
    if not await session_mgr.is_token_valid(sid):
        await sio.emit('error', {'message': 'Invalid or expired token'}, to=sid)
        await sio.disconnect(sid)
        return

    user = session_mgr.sid_role_map.get(sid)
    if not user:
        await sio.emit("error", {"message": "Unauthorized"}, to=sid)
        await sio.disconnect(sid)
        return
    request_type = data.get("request_type")
    camera_id = data.get("camera_id")


    if not camera_id and request_type in ["live", "plates_data"]:
        await sio.emit("error", {"message": "camera_id is required for this request_type"}, to=sid)
        return

    if user.user_type == UserType.VIEWER:
        async with nats_session() as session:
            query = await session.execute(
                select(DBCamera).where(DBCamera.id == int(camera_id)).options(selectinload(DBCamera.gate))
            )
            camera = query.scalar_one_or_none()
            if not camera:
                await sio.emit("error", {"message": "Camera not found"}, to=sid)
                return
            if camera.gate.id not in [gate.id for gate in user.gates]:
                await sio.emit("error", {"message": "Access denied to this camera"}, to=sid)
                return

    # Use distinct rooms for different data types
    if request_type == "resources":
        await sio.enter_room(sid, f"camera-{camera_id}-resources")
        logger.info(f"Client {sid} subscribed to resources")
        await sio.emit("request_acknowledged", {"status": "subscribed", "data_type": "resources"}, to=sid)
        return

    elif request_type == "heartbeat":
        await sio.enter_room(sid, f"camera-{camera_id}-heartbeat")
        logger.info(f"Client {sid} subscribed to heartbeat data")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "heartbeat"}, to=sid)
        return



    elif request_type == "camera_connection":
        await sio.enter_room(sid, f"camera-{camera_id}-camera_connection")
        logger.info(f"Client {sid} subscribed to camera_connection data")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "camera_connection"}, to=sid)

    elif request_type == "live":
        await _handle_camera_subscription(sid, camera_id, request_type, data)
        await sio.enter_room(sid, f"camera-{camera_id}-live")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "live"}, to=sid)

    elif request_type == "plates_data":
        await sio.enter_room(sid, f"camera-{camera_id}-plate")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "plate"}, to=sid)

    elif request_type == "recording":
        logger.error("[ERROR] Cannot send command: Client not authenticated or connected.")

    else:
        await sio.emit('error', {'message': 'Invalid request_type'}, to=sid)


@sio.event
async def unsubscribe(sid, data):
    """
    Event triggered when a client wants to unsubscribe from a specific data stream.
    """
    request_type = data.get("request_type")
    camera_id = data.get("camera_id")

    if not request_type or not camera_id:
        await sio.emit("error", {"message": "Invalid request. 'request_type' and 'camera_id' are required."}, to=sid)
        return

    # Determine the room name based on the request type
    room_name = None
    if request_type == "resources":
        room_name = f"camera-{camera_id}-resources"
    elif request_type == "heartbeat":
        room_name = f"camera-{camera_id}-heartbeat"
    elif request_type == "camera_connection":
        room_name = f"camera-{camera_id}-camera_connection"
    elif request_type == "live":
        room_name = f"camera-{camera_id}-live"
    elif request_type == "plates_data":
        room_name = f"camera-{camera_id}-plate"
    else:
        await sio.emit("error", {"message": f"Unknown request_type: {request_type}"}, to=sid)
        return

    # Leave the room
    await sio.leave_room(sid, room_name)
    logger.info(f"Client {sid} unsubscribed from {request_type} data for camera_id {camera_id}")
    await sio.emit("unsubscribe_acknowledged", {"status": "unsubscribed", "data_type": request_type}, to=sid)


async def stop_workers():
    global worker_running
    worker_running = False
    # No message queue or worker to stop


async def emit_to_requested_sids(event_name, data, camera_id=None):
    if event_name not in ["resources", "heartbeat"]:
        camera_id = data.get("camera_id")
        if not camera_id:
            return

    if event_name == "resources":
        lpr_id = data["lpr_id"]
        await sio.emit("resources", data, room=f"camera-{lpr_id}-resources")
    elif event_name == "heartbeat":
        lpr_id = data["lpr_id"]
        await sio.emit("heartbeat", data, room=f"camera-{lpr_id}-heartbeat")
        logger.info(f"Emitted heartbeat to all subscribed clients")

    elif event_name == "camera_connection":
        await sio.emit("camera_connection", data, room=f"camera-{camera_id}-camera_connection")
        logger.info(f"Emitted camera_connection to all subscribed clients")
    # Emit to the appropriate room based on data_type
    if event_name == "live":
        await sio.emit("live", data, room=f"camera-{camera_id}-live")
    elif event_name == "plates_data":
        await sio.emit("plates_data", data, room=f"camera-{camera_id}-plate")
    else:
        logger.warning(f"[WARNING] Unknown data_type {event_name}. No emission done.")



async def start_background_tasks():
    logger.info("[INFO] Starting background tasks...")
    # Start the token expiration handler
    asyncio.create_task(session_mgr.handle_expirations())
    logger.info("[INFO] Background tasks started.")


async def publish_message_to_nats(command_data, lpr_id):


    global nats_client

    command_subject = "command." + str(lpr_id)
    command_json = _create_command_message(command_data)
    try:
        await nats_client.publish(command_subject, command_json)
    except OutboundBufferLimitError:
        print("Buffer limit exceeded! Retrying...")
        await asyncio.sleep(1)
    camid = command_data["cameraId"]
    logger.info(f"Client {nats_client} subscribed to live data for camera_id {camid}")


async def _handle_camera_subscription(sid, camera_id, request_type, data):
    """Handle subscription to camera-specific events."""
    command_data = {
        "commandType": "streaming",
        "cameraId": camera_id,
        "duration": data.get("duration"),
    }
    async with nats_session() as session:
        query = await session.execute(
            select(DBCamera).where(DBCamera.id == int(camera_id)).options(selectinload(DBCamera.lpr))
        )
        db_camera = query.scalar_one_or_none()

        if not db_camera:
            await sio.emit("error", {"message": "camera not found"}, to=sid)
            return

        lpr = db_camera.lpr

        if not(lpr and lpr.is_active):
            logger.info(f"{lpr} not found")

    await publish_message_to_nats(command_data, lpr.id)
    logger.info(f"Client {sid} subscribed to live data for camera_id {camera_id}")
    # await sio.emit("request_acknowledged", {"status": "subscribed", "data_type": request_type, "camera_id": camera_id}, to=sid)
