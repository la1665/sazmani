from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authorization import get_current_active_user, get_admin_user, get_admin_or_staff_user
from database.engine import get_db
from schema.user import UserInDB
from schema.camera import CameraPagination
from schema.lpr import LprCreate, LprUpdate, LprInDB, LprPagination
from schema.lpr_setting import LprSettingInstanceCreate, LprSettingInstanceUpdate, LprSettingInstanceInDB, LprSettingInstancePagination
from crud.lpr import LprOperation
from utils.middlewwares import check_password_changed
from tcp.tcp_manager import add_connection, update_connection, remove_connection

# Create an APIRouter for user-related routes
lpr_router = APIRouter(
    prefix="/v1/lprs",
    tags=["lprs"],
)



#lpr endpoints
@lpr_router.post("/", response_model=LprInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_lpr(
    lpr: LprCreate,
    db: AsyncSession = Depends(get_db),
    current_user:UserInDB=Depends(get_admin_user)
):
    lpr_op = LprOperation(db)
    new_lpr = await lpr_op.create_lpr(lpr)
    await add_connection(db, lpr_id=new_lpr.id)
    return new_lpr

@lpr_router.get("/", response_model=LprPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_lprs(
    page: int=1,
    page_size: int=10,
    db: AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_or_staff_user)
):
    lpr_op = LprOperation(db)
    return await lpr_op.get_all_objects(page, page_size)

@lpr_router.get("/{lpr_id}", response_model=LprInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_lpr(
    lpr_id: int,
    db: AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_or_staff_user)
):
    lpr_op = LprOperation(db)
    return await lpr_op.get_one_object_id(lpr_id)


@lpr_router.get("/{lpr_id}/cameras", response_model=CameraPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_lpr_all_cameras(lpr_id: int, page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    lpr_op = LprOperation(db)
    return await lpr_op.get_lpr_all_cameras(lpr_id, page, page_size)


@lpr_router.put("/{lpr_id}", response_model=LprInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_lpr(
    lpr_id: int,
    lpr: LprUpdate,
    db:AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_user)
):
    lpr_op = LprOperation(db)
    db_lpr = await lpr_op.update_lpr(lpr_id, lpr)
    await update_connection(db, lpr_id=db_lpr.id)
    return db_lpr

@lpr_router.delete("/{lpr_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_lpr(
    lpr_id: int,
    db:AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_user)
):
    lpr_op = LprOperation(db)
    await remove_connection(lpr_id)
    db_lpr = await lpr_op.delete_lpr(lpr_id)
    return db_lpr

@lpr_router.patch("/{lpr_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    lpr_id: int,
    db:AsyncSession=Depends(get_db),
    current_user:UserInDB=Depends(get_admin_user)
):
    lpr_op = LprOperation(db)
    status = await lpr_op.change_activation_status(lpr_id)
    if status["message"] == "activated":
        await add_connection(db, lpr_id)
        return status
    else:
        await remove_connection(lpr_id)
        return status

@lpr_router.get("/{lpr_id}/settings", response_model=LprSettingInstancePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_lpr_all_settings(lpr_id: int, page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    lpr_op = LprOperation(db)
    return await lpr_op.get_lpr_all_settings(lpr_id, page, page_size)

@lpr_router.post("/{lpr_id}/settings", response_model=LprSettingInstanceInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_add_lpr_setting(
    lpr_id: int,
    setting_create: LprSettingInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user),
):
    lpr_op = LprOperation(db)
    return await lpr_op.add_lpr_setting(lpr_id, setting_create)

@lpr_router.put("/{lpr_id}/settings/{setting_id}", response_model=LprSettingInstanceInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_lpr_setting(
    lpr_id: int,
    setting_id: int,
    setting_update: LprSettingInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user),
):
    lpr_op = LprOperation(db)
    return await lpr_op.update_lpr_setting(lpr_id, setting_id, setting_update)

@lpr_router.delete("/{lpr_id}/settings/{setting_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_remove_camera_setting(
    lpr_id: int,
    setting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user),
):
    lpr_op = LprOperation(db)
    return await lpr_op.remove_lpr_setting(lpr_id, setting_id)
