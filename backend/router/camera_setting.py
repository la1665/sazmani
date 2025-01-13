from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authorization import get_current_active_user, get_admin_user, get_admin_or_staff_user
from database.engine import get_db
from schema.user import UserInDB
from schema.camera_setting import CameraSettingCreate, CameraSettingUpdate, CameraSettingInDB, CameraSettingPagination
from crud.camera_setting import CameraSettingOperation
from utils.middlewwares import check_password_changed



camera_setting_router = APIRouter(
    prefix="/v1/camera-settings",
    tags=["camera settings"],
)


# camera setting endpoints
@camera_setting_router.post("/", response_model=CameraSettingInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_setting(setting: CameraSettingCreate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = CameraSettingOperation(db)
    return await setting_op.create_setting(setting)

@camera_setting_router.get("/", response_model=CameraSettingPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_settings(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = CameraSettingOperation(db)
    return await setting_op.get_all_objects(page, page_size)


@camera_setting_router.get("/{setting_id}", response_model=CameraSettingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_setting(setting_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = CameraSettingOperation(db)
    return await setting_op.get_one_object_id(setting_id)


@camera_setting_router.put("/{setting_id}", response_model=CameraSettingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_setting(setting_id: int, setting: CameraSettingUpdate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = CameraSettingOperation(db)
    return await setting_op.update_setting(setting_id, setting)


@camera_setting_router.delete("/{setting_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_setting(setting_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = CameraSettingOperation(db)
    return await setting_op.delete_object(setting_id)
