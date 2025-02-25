import socketio
import logging
import asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError

# from auth.auth import jwt, JWTError
from settings import settings
from database.engine import async_session
from models.user import DBUser, UserType
from models.camera import DBCamera
from shared_resources import connections

logger = logging.getLogger(__name__)

# Create a new instance of an ASGI-compatible Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",  # Use ASGI mode for FastAPI compatibility
    cors_allowed_origins="*",  # Allow all origins for CORS; adjust as needed
    logger=True,
    engineio_logger=True,
)

# Maps to manage client subscriptions
request_map = {
    "live": {},  # Format: {"sid": {cameraID1, cameraID2, ...}}
    "plates_data": {},  # Format: {"sid": {cameraID1, cameraID2, ...}}
    "resources": set(),
    "heartbeat": {},  # heartbeat don't require camera IDs
    "camera_connection": {},  # camera_connection don't require camera IDs
}

sid_role_map = {}  # Maps SID to roles (e.g., {"sid1": "admin", "sid2": "operator"})

async def validate_and_get_user(token: str):
    """Validates a JWT token and retrieves the user from the database."""
    try:
        if not settings.SECRET_KEY or not settings.ALGORITHM:
            raise ValueError("SECRET_KEY and ALGORITHM must be set in the settings.")

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        personal_number = payload.get("sub")
        if not personal_number:
            raise ValueError("Invalid token: Missing 'sub'")
        async with async_session() as session:
            query = await session.execute(
                select(DBUser).where(DBUser.personal_number == personal_number).options(selectinload(DBUser.gates))
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
        sid_role_map[sid] = user
        logger.info(f"Client {sid} connected with role {user.user_type}")
        await sio.emit("connection_ack", {"message": "Connected"}, to=sid)

    except ValueError as e:
        logger.error(f"Connection error for SID {sid}: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)
        await sio.disconnect(sid)


@sio.event
async def disconnect(sid):
    """
    Event triggered when a client disconnects from the WebSocket.
    """
    sid_role_map.pop(sid, None)
    for key in request_map:
        request_map[key].pop(sid, None)
    logger.info(f"Client {sid} disconnected")


@sio.event
async def subscribe(sid, data):
    """
    Allows clients to subscribe to specific events.
    """
    global connections
    print(f"Received subscription request from {sid}: {data}")

    user = sid_role_map.get(sid)
    if not user:
        await sio.emit("error", {"message": "Unauthorized"}, to=sid)
        return

    request_type = data.get("request_type")
    camera_id = data.get("camera_id")

    if request_type not in request_map:
        await sio.emit("error", {"message": "Invalid request_type"}, to=sid)
        return

    if not camera_id and request_type in ["live", "plates_data"]:
        await sio.emit("error", {"message": "camera_id is required for this request_type"}, to=sid)
        return

    # Check access for Viewer role
    if user.user_type == UserType.VIEWER:
        async with async_session() as session:
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


    if request_type == "resources":
        request_map["resources"].add(sid)
        logger.info(f"Client {sid} subscribed to resources")
        await sio.emit("request_acknowledged", {"status": "subscribed", "data_type": "resources"}, to=sid)
        return

    if request_type == "heartbeat":
        request_map["heartbeat"].setdefault(sid, set())
        logger.info(f"Client {sid} subscribed to heartbeat data")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "heartbeat"}, to=sid)
        return

    if request_type == "camera_connection":
        request_map["camera_connection"].setdefault(sid, set())
        logger.info(f"Client {sid} subscribed to camera_connection data")
        await sio.emit('request_acknowledged', {"status": "subscribed", "data_type": "camera_connection"}, to=sid)
        return

    # if not camera_id:
    #     await sio.emit("error", {"message": "camera_id is required"}, to=sid)
    #     return

    request_map[request_type].setdefault(sid, set()).add(camera_id)

    if request_type == "live":
        await _handle_camera_subscription(sid, camera_id, request_type, data)
    elif request_type == "plates_data":
        logger.info(f"Client {sid} subscribed to plate data for camera_id {camera_id}")
        await sio.emit("request_acknowledged", {"status": "subscribed", "data_type": "plates_data", "camera_id": camera_id}, to=sid)


@sio.event
async def unsubscribe(sid, data):
    """
    Allows clients to unsubscribe from specific events.
    """
    request_type = data.get("request_type")
    camera_id = data.get("camera_id")

    if request_type not in request_map:
        await sio.emit("error", {"message": "Invalid request_type"}, to=sid)
        return

    if request_type == "heartbeat":
        request_map["heartbeat"].discard(sid)
        logger.info(f"Client {sid} unsubscribed from heartbeat")
        await sio.emit("request_acknowledged", {"status": "unsubscribed", "data_type": "heartbeat"}, to=sid)
        return

    if request_type == "resources":
        request_map["resources"].discard(sid)
        logger.info(f"Client {sid} unsubscribed from resources")
        await sio.emit("request_acknowledged", {"status": "unsubscribed", "data_type": "resources"}, to=sid)
        return

    if request_type == "camera_connection":
        request_map["camera_connection"].discard(sid)
        logger.info(f"Client {sid} unsubscribed from camera_connection")
        await sio.emit("request_acknowledged", {"status": "unsubscribed", "data_type": "camera_connection"}, to=sid)
        return

    if sid in request_map[request_type]:
        request_map[request_type][sid].discard(camera_id)
        if not request_map[request_type][sid]:
            del request_map[request_type][sid]
        logger.info(f"Client {sid} unsubscribed from {request_type} for camera_id {camera_id}")
        await sio.emit("request_acknowledged", {"status": "unsubscribed", "data_type": request_type, "camera_id": camera_id}, to=sid)
        return

async def _handle_camera_subscription(sid, camera_id, request_type, data):
    """Handle subscription to camera-specific events."""
    command_data = {
        "commandType": "streaming",
        "cameraId": camera_id,
        "duration": data.get("duration"),
    }
    async with async_session() as session:
        query = await session.execute(
            select(DBCamera).where(DBCamera.id == int(camera_id)).options(selectinload(DBCamera.lpr))
        )
        db_camera = query.scalar_one_or_none()

        if not db_camera:
            await sio.emit("error", {"message": "camera not found"}, to=sid)
            return

        lpr = db_camera.lpr
        if lpr and lpr.is_active:
            print(f"lpr: {lpr.id}")
            print(f"connections are {connections}")
            if lpr.id in connections:
                factory = connections[lpr.id]
                if factory.authenticated and factory.active_protocol:
                    print(f"[INFO] Sending command to server: {command_data}")
                    factory.active_protocol.send_command(command_data)
                else:
                    print("[ERROR] Cannot send command: Client is not authenticated or connected.")
            else:
                print(f"[ERROR] No connection for LPR ID {lpr.id}")

    logger.info(f"Client {sid} subscribed to live data for camera_id {camera_id}")
    await sio.emit("request_acknowledged", {"status": "subscribed", "data_type": request_type, "camera_id": camera_id}, to=sid)


async def emit_to_requested_sids(event_name, data, camera_id=None):
    """
    Emits an event with data to all clients subscribed to the event.
    """
    if event_name not in request_map:
        logger.error(f"Invalid event name: {event_name}")
        return

    if event_name == "resources":
        for sid in request_map["resources"]:
            await sio.emit(event_name, data, to=sid)

    elif event_name == "heartbeat":
        for sid in request_map[event_name]:
            asyncio.create_task(sio.emit(event_name, data, to=sid))
        logger.info(f"Emitted heartbeat to all subscribed clients")

    elif event_name == "camera_connection":
        for sid in request_map[event_name]:
            asyncio.create_task(sio.emit(event_name, data, to=sid))
        logger.info(f"Emitted camera_connection to all subscribed clients")

    else:
        tasks = []
        for sid, camera_ids in request_map[event_name].items():
            if camera_id is None or camera_id in camera_ids:
                tasks.append(asyncio.create_task(sio.emit(event_name, data, to=sid)))
                logger.info(f"Emitted {event_name} to SID {sid} for camera_id {camera_id}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"Emitted {event_name} to all subscribed clients")
