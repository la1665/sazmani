from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from settings import settings
from database.engine import get_db
from schema.vehicle import VehicleCreate, VehiclePagination, VehicleInDB
from crud.vehicle import VehicleOperation
from schema.user import UserInDB
from auth.authorization import get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only
from utils.middlewwares import check_password_changed


# Create an APIRouter for user-related routes
vehicle_router = APIRouter(
    prefix="/v1/vehicles",
    tags=["vehicles"],
)


@vehicle_router.post("/", response_model=VehicleInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_vehicle(
    vehicle: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Create a new vehicle.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.create_vehicle(vehicle)



@vehicle_router.get("/{plate_number}", response_model=VehicleInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_vehicle(
    request: Request,
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

    if vehicle.car_image:
        filename = Path(vehicle.car_image).name
        vehicle.car_image_url = f"{request.base_url}uploads/car_images/{filename}"

    return vehicle


@vehicle_router.get("/",response_model=VehiclePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_vehicles(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Retrieve all vehicles with pagination.
    """
    vehicle_op = VehicleOperation(db)
    result = await vehicle_op.get_all_objects(page, page_size)
    for vehicle in result["items"]:
        if vehicle.car_image:
            filename = Path(vehicle.car_image).name
            vehicle.car_image_url = f"{request.base_url}uploads/car_images/{filename}"
    return result


@vehicle_router.patch("/{vehicle_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    vehicle_id: int,
    db:AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_or_staff_user)
):
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.change_activation_status(vehicle_id)


@vehicle_router.delete("/{vehicle_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Delete a vehicle by ID.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.delete_object(vehicle_id)


@vehicle_router.post("/{vehicle_id}/car-image", response_model=VehicleInDB, dependencies=[Depends(check_password_changed)])
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
