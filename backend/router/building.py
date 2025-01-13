from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authorization import get_current_active_user, get_admin_user, get_admin_or_staff_user
from database.engine import get_db
from schema.gate import GatePagination
from schema.user import UserInDB
from schema.building import BuildingCreate, BuildingUpdate, BuildingInDB, BuildingPagination
from crud.building import BuildingOperation
from utils.middlewwares import check_password_changed


building_router = APIRouter(
    prefix="/v1/buildings",
    tags=["buildings"],
)


@building_router.post("/", response_model=BuildingInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_building(building: BuildingCreate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.create_building(building)

@building_router.get("/", response_model=BuildingPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_buildings(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.get_all_objects(page, page_size)


@building_router.get("/{building_id}", response_model=BuildingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_building(building_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.get_one_object_id(building_id)


@building_router.get("/{building_id}/gates", response_model=GatePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_building_all_gates(building_id: int, page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.get_building_all_gates(building_id, page, page_size)


@building_router.put("/{building_id}", response_model=BuildingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_building(building_id: int, building: BuildingUpdate, db:AsyncSession=Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.update_building(building_id, building)


@building_router.delete("/{building_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_building(building_id: int, db:AsyncSession=Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    building_op = BuildingOperation(db)
    return await building_op.delete_object(building_id)

@building_router.patch("/{building_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    building_id: int,
    db: AsyncSession=Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    building_op = BuildingOperation(db)
    return await building_op.change_activation_status(building_id)
