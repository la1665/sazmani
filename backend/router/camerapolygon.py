from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Optional
from crud.camera import CameraOperation
from schema.camera import CameraInDB
from schema.camerapolygon import CameraPolygonInDB
from database.engine import get_db
from utils.middlewares import check_password_changed


polygon_router = APIRouter(
    prefix="/v1/polygon",
    tags=["polygon"],
)

@polygon_router.get(
    "/camera/{camera_id}/polygon",
    response_model=CameraPolygonInDB,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_password_changed)]
)
async def get_camera_polygon(
    request: Request,
    camera_id: int,
    db_session: AsyncSession = Depends(get_db)
):
    proto = request.headers.get("X-Forwarded-Proto", "http")

    # Extract the base URL and normalize it to include port 8000
    raw_base_url = str(request.base_url).rstrip("/")
    base_url_without_port = raw_base_url.split("//")[1].split(":")[0]
    nginx_base_url = f"{proto}://{base_url_without_port}:8000/"

    camera_operation = CameraOperation(db_session)
    db_camera = await camera_operation.get_one_object_id(camera_id)

    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    crud_image_url = f"{nginx_base_url}{db_camera.crud_image}" if db_camera.crud_image else None

    # Fetch points directly from the Camera model (not CameraPolygon anymore)
    points = db_camera.get_points() if db_camera.points else []

    return {
        "camera_id": camera_id,
        "crud_image": crud_image_url,  # Return None if not found
        "polygon_points": points  # Return points directly from Camera model
    }


@polygon_router.put(
    "/camera/{camera_id}/polygon",
    response_model=CameraInDB,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_password_changed)]
)
async def update_camera_polygon(
        camera_id: int,
        points: Optional[List[Tuple[int, int]]] = None,  # Handle (x, y) points
        db_session: AsyncSession = Depends(get_db)
):
    camera_operation = CameraOperation(db_session)
    db_camera = await camera_operation.get_one_object_id(camera_id)

    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    if points is not None:
        # Update points directly in the Camera object
        db_camera.set_points(points)

    # Commit the update to the database
    await db_session.commit()
    await db_session.refresh(db_camera)

    return CameraInDB.from_orm(db_camera)
