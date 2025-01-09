from fastapi import APIRouter, Depends, status, HTTPException
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
    plate_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Retrieve a vehicle by plate.
    """
    vehicle_op = VehicleOperation(db)
    return await vehicle_op.get_one_vehcile_plate(plate_number)


@vehicle_router.get("/",response_model=VehiclePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_vehicles(
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
    return result



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
