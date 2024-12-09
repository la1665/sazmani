from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CrudOperation
from models.camera_setting import DBCameraSetting
from schema.camera_setting import CameraSettingCreate, CameraSettingUpdate


class CameraSettingOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBCameraSetting)



    async def create_setting(self, camera_setting: CameraSettingCreate):
        db_camera_setting = await self.get_one_object_name(camera_setting.name)
        if db_camera_setting:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "camera-setting already exists.")
        try:
            new_setting = DBCameraSetting(
            name=camera_setting.name,
            description=camera_setting.description,
            value=camera_setting.value,
            setting_type=camera_setting.setting_type
            )
            self.db_session.add(new_setting)
            await self.db_session.commit()
            await self.db_session.refresh(new_setting)
            return new_setting
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"{error}: Could not create camera-setting")
        finally:
            await self.db_session.close()

    async def update_setting(self, setting_id: int, camera_setting: CameraSettingUpdate):
        db_camera_setting = await self.get_one_object_id(setting_id)
        try:
            update_data = camera_setting.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_camera_setting, key, value)
            self.db_session.add(db_camera_setting)
            await self.db_session.commit()
            await self.db_session.refresh(db_camera_setting)
            return db_camera_setting
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"{error}: Could not update camera-setting")
        finally:
            await self.db_session.close()
