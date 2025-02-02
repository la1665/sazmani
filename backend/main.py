import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

from lifespan import lifespan
from socket_managment_nats_ import sio
from router.base import include_router
from router.auth import auth_router
from router.user import user_router
from router.guest import guest_router
from router.building import building_router
from router.gate import gate_router
from router.camera import camera_router
from router.lpr import lpr_router
from router.relay import relay_router
from router.status import status_router
from router.key import relay_key_router
from router.vehicle import vehicle_router
from router.traffic import traffic_router
from router.record import record_router
from router.search import search_router


app = FastAPI(
    title="Sazman",
    description="License Plate Reader",
    lifespan=lifespan
)

# from utils.middlewares import SecurityMiddleware
# app.add_middleware(SecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories for images
BASE_UPLOAD_DIR = Path("uploads")
PROFILE_IMAGE_DIR = BASE_UPLOAD_DIR / "profile_images"
CAR_IMAGE_DIR = BASE_UPLOAD_DIR / "car_images"
CAR_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
PLATE_IMAGE_DIR = BASE_UPLOAD_DIR / "plate_images"
PLATE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
TRAFFIC_IMAGE_DIR = BASE_UPLOAD_DIR / "traffic_images"
TRAFFIC_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR = BASE_UPLOAD_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
ZIP_FILE_DIR = BASE_UPLOAD_DIR / "zips"
ZIP_FILE_DIR.mkdir(parents=True, exist_ok=True)
# Serve static files for profile and plate images
app.mount("/uploads/profile_images", StaticFiles(directory=str(PROFILE_IMAGE_DIR)), name="profile_images")
app.mount("/uploads/car_images", StaticFiles(directory=str(CAR_IMAGE_DIR)), name="car_images")
app.mount("/uploads/plate_images", StaticFiles(directory=str(PLATE_IMAGE_DIR)), name="plate_images")
app.mount("/uploads/traffic_images", StaticFiles(directory=str(TRAFFIC_IMAGE_DIR)), name="traffic_images")
app.mount("/uploads/recordings", StaticFiles(directory=str(RECORDINGS_DIR)), name="recordings")
app.mount("/uploads/zips", StaticFiles(directory=str(ZIP_FILE_DIR)), name="zips")



include_router(app, auth_router)
include_router(app, user_router)
include_router(app, guest_router)
include_router(app, building_router)
include_router(app, gate_router)
include_router(app, camera_router)
include_router(app, lpr_router)
include_router(app, relay_router)
include_router(app, status_router)
include_router(app, relay_key_router)
include_router(app, vehicle_router)
include_router(app, traffic_router)
include_router(app, record_router)
include_router(app, search_router)

@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"message": "Welcome to the Sazman API!"}


app_socket = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path="/socket.io"
)

def main():
    """
    Main entry point for running the FastAPI app.
    """
    uvicorn.run("main:app_socket", host="0.0.0.0", port=8000, log_level="debug")
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="debug")


if __name__ == "__main__":
    main()
