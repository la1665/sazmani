from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authorization import get_current_active_user, get_admin_user, get_admin_or_staff_user
from database.engine import get_db
from schema.user import UserInDB
from schema.lpr_setting import LprSettingCreate, LprSettingUpdate, LprSettingInDB, LprSettingPagination
from crud.lpr_setting import LprSettingOperation
from utils.middlewwares import check_password_changed



lpr_setting_router = APIRouter(
    prefix="/v1/lpr-settings",
    tags=["lpr settings"],
)


# camera setting endpoints
@lpr_setting_router.post("/", response_model=LprSettingInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_setting(setting: LprSettingCreate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_user)):
    setting_op = LprSettingOperation(db)
    return await setting_op.create_setting(setting)

@lpr_setting_router.get("/", response_model=LprSettingPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_settings(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = LprSettingOperation(db)
    return await setting_op.get_all_objects(page, page_size)


@lpr_setting_router.get("/{setting_id}", response_model=LprSettingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_setting(setting_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    setting_op = LprSettingOperation(db)
    return await setting_op.get_one_object_id(setting_id)


@lpr_setting_router.put("/{setting_id}", response_model=LprSettingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_setting(setting_id: int, setting: LprSettingUpdate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_user)):
    setting_op = LprSettingOperation(db)
    return await setting_op.update_setting(setting_id, setting)


@lpr_setting_router.delete("/{setting_id}", response_model=LprSettingInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_setting(setting_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_user)):
    setting_op = LprSettingOperation(db)
    return await setting_op.delete_object(setting_id)
