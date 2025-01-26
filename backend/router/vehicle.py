from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from settings import settings
from database.engine import get_db
from schema.vehicle import VehicleCreate, VehiclePagination, VehicleInDB
from crud.vehicle import VehicleOperation
from schema.user import UserInDB
from auth.authorization import get_admin_or_staff_user, get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only, get_current_active_user
from utils.middlewares import check_password_changed
from models.user import UserType


vehicle_router = APIRouter(
    prefix="/v1",
    tags=["vehicles"],
)


@vehicle_router.post("/users/{user_id}/vehicles", response_model=VehicleInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_vehicle(
    user_id: int,
    vehicle: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Create a new vehicle.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.create_vehicle(vehicle)


@vehicle_router.get("/vehicles",response_model=VehiclePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_user_all_vehicles(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_current_active_user)
):
    """
    Retrieve all vehicles of a specific user by user ID.
    Accessible by: Admin, Staff, or Self User.
    """
    vehicle_op = VehicleOperation(db)
    if user_id:
        # Fetch vehicles for a specific user
        if current_user.user_type in [UserType.ADMIN, UserType.STAFF] or current_user.id == user_id:
            result = await vehicle_op.get_vehicles_by_user(user_id, page, page_size)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Unable to retrieve vehicles for this user.",
            )
    else:
        # Fetch all vehicles (admin/staff only)
        if current_user.user_type in [UserType.ADMIN, UserType.STAFF]:
            result = await vehicle_op.get_all_objects(page, page_size)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Unable to retrieve all vehicles.",
            )

    for vehicle in result["items"]:
        if vehicle.car_image:
            vehicle.car_image_url = f"{request.base_url}{vehicle.car_image}"
    return result


@vehicle_router.get("/users/{user_id}/vehicles/{plate_number}", response_model=VehicleInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_vehicle(
    request: Request,
    user_id: int,
    plate_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Retrieve a vehicle by plate.
    """
    vehicle_op = VehicleOperation(db)
    vehicle = await vehicle_op.get_one_vehcile_plate(plate_number)
    if not vehicle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found!")

    if current_user.user_type not in [UserType.ADMIN, UserType.STAFF] and vehicle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You cannot view this resource.",
        )
    if vehicle.car_image:
        vehicle.car_image_url = f"{request.base_url}{vehicle.car_image}"

    return vehicle


@vehicle_router.patch("/users/vehicles/{vehicle_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    vehicle_id: int,
    db:AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_or_staff_user)
):
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.change_activation_status(vehicle_id)


@vehicle_router.delete("/users/{user_id}/vehicles/{vehicle_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_vehicle(
    user_id: int,
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Delete a vehicle by ID.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.delete_object(vehicle_id)


@vehicle_router.post("/users/{user_id}/vehicles/{vehicle_id}/car-image", response_model=VehicleInDB, dependencies=[Depends(check_password_changed)])
async def api_upload_car_image(
    vehicle_id: int,
    car_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_self_user_only)
):
    """
    Upload or update the car's image.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.upload_vehicle_image(vehicle_id, car_image)
