from tcp import reactor_setup
import threading
import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

from lifespan import lifespan
from socket_management import sio
from router.base import include_router
from router.auth import auth_router
from router.user import user_router
from router.building import building_router
from router.gate import gate_router
from router.camera import camera_router
from router.lpr import lpr_router
from router.vehicle import vehicle_router
from router.traffic import traffic_router
from task_manager.celery_app import celery, add_numbers

# start_reactor()
# reactor_setup_func()

app = FastAPI(
    title="Sazman",
    description="License Plate Reader",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"[DEBUG] Reactor is running in thread: {threading.current_thread().name}")

# Directories for images
BASE_UPLOAD_DIR = Path("uploads")
PROFILE_IMAGE_DIR = BASE_UPLOAD_DIR / "profile_images"
PLATE_IMAGE_DIR = BASE_UPLOAD_DIR / "plate_images"
# Serve static files for profile and plate images
app.mount("/uploads/profile_images", StaticFiles(directory=str(PROFILE_IMAGE_DIR)), name="profile_images")
app.mount("/uploads/plate_images", StaticFiles(directory=str(PLATE_IMAGE_DIR)), name="plate_images")



include_router(app, auth_router)
include_router(app, user_router)
include_router(app, building_router)
include_router(app, gate_router)
include_router(app, camera_router)
include_router(app, lpr_router)
include_router(app, vehicle_router)
include_router(app, traffic_router)

@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"message": "Welcome to the Sazman API!"}

@app.get("/add/")
async def add(a: int, b: int):
    task = add_numbers.delay(a, b)
    return {"task_id": task.id, "status": "Task submitted"}

@app.get("/get-task-result/")
async def get_task_result(task_id: str):
    from celery.result import AsyncResult

    # Get task result using the task ID
    task_result = AsyncResult(task_id, app=celery)

    if task_result.state == "PENDING":
        return {"task_id": task_id, "status": "Task is still running"}
    elif task_result.state == "SUCCESS":
        return {"task_id": task_id, "status": "Task completed", "result": task_result.result}
    elif task_result.state == "FAILURE":
        return {"task_id": task_id, "status": "Task failed", "error": str(task_result.info)}
    else:
        return {"task_id": task_id, "status": task_result.state}

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
