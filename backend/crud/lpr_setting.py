from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


from crud.base import CrudOperation
from models.lpr_setting import DBLprSetting
from schema.lpr_setting import LprSettingCreate, LprSettingUpdate


class LprSettingOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBLprSetting, None)



    async def create_setting(self, lpr_setting: LprSettingCreate):
        db_lpr_setting = await self.get_one_object_name(lpr_setting.name)
        if db_lpr_setting:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "lpr-setting already exists.")
        try:
            new_setting = DBLprSetting(
            name=lpr_setting.name,
            description=lpr_setting.description,
            value=lpr_setting.value,
            setting_type=lpr_setting.setting_type
            )
            self.db_session.add(new_setting)
            await self.db_session.commit()
            await self.db_session.refresh(new_setting)
            return new_setting
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"{error}: Could not create lpr-setting")
        finally:
            await self.db_session.close()

    async def update_setting(self, setting_id: int, lpr_setting: LprSettingUpdate):
        db_lpr_setting = await self.get_one_object_id(setting_id)
        try:
            update_data = lpr_setting.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_lpr_setting, key, value)
            self.db_session.add(db_lpr_setting)
            await self.db_session.commit()
            await self.db_session.refresh(db_lpr_setting)
            return db_lpr_setting
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"{error}: Could not update lpr-setting")
        finally:
            await self.db_session.close()
