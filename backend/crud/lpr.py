import math
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from settings import settings
from crud.base import CrudOperation
from models.lpr_setting import DBLprSetting, DBLprSettingInstance
from models.camera import DBCamera
from models.lpr import DBLpr
from schema.lpr import LprUpdate, LprCreate, LprInDB
from schema.lpr_setting import LprSettingInstanceCreate, LprSettingInstanceUpdate, LprSettingInstanceInDB
from search_service.search_config import lpr_search, lpr_setting_search

class LprOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBLpr, lpr_search)

    async def create_lpr(self, lpr:LprCreate):
        db_lpr = await self.get_one_object_name(lpr.name)
        if db_lpr:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "lpr already exists.")

        try:
            new_lpr = self.db_table(
                name=lpr.name,
                ip=lpr.ip,
                port=lpr.port,
                auth_token=settings.LPR_AUTH_TOKEN,
                latitude=lpr.latitude,
                longitude=lpr.longitude,
                description=lpr.description,
            )

            self.db_session.add(new_lpr)
            await self.db_session.flush()

            query = await self.db_session.execute(select(DBLprSetting))
            default_settings = query.unique().scalars().all()
            for setting in default_settings:
                setting_instance = DBLprSettingInstance(
                    lpr_id=new_lpr.id,
                    name=setting.name,
                    description=setting.description,
                    value=setting.value,
                    setting_type=setting.setting_type,
                    is_active=setting.is_active,
                    default_setting_id=setting.id
                )
                self.db_session.add(setting_instance)
                await self.db_session.flush()
                meilisearch_setting = LprSettingInstanceInDB.from_orm(setting_instance)
                await lpr_setting_search.sync_document(meilisearch_setting)


            await self.db_session.commit()
            await self.db_session.refresh(new_lpr)
            meilisearch_lpr = LprInDB.from_orm(new_lpr)
            await lpr_search.sync_document(meilisearch_lpr)
            return new_lpr
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create lpr.")
        finally:
            await self.db_session.close()


    async def update_lpr(self, lpr_id: int, lpr_update: LprUpdate):
        db_lpr = await self.get_one_object_id(lpr_id)
        try:
            for key, value in lpr_update.dict(exclude_unset=True).items():
                setattr(db_lpr, key, value)
            self.db_session.add(db_lpr)
            await self.db_session.commit()
            await self.db_session.refresh(db_lpr)
            meilisearch_lpr = LprInDB.from_orm(db_lpr)
            await lpr_search.sync_document(meilisearch_lpr)

            return db_lpr
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update lpr."
            )
        finally:
            await self.db_session.close()

    async def delete_lpr(self, lpr_id: int):
        db_lpr = await self.get_one_object_id(lpr_id)
        try:
            await self.db_session.delete(db_lpr)
            await self.db_session.commit()

            # Remove connection from Twisted
            # remove_connection(lpr_id)

            return {"message": f"LPR {lpr_id} deleted successfully"}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to delete LPR.")
        finally:
            await self.db_session.close()



    async def get_lpr_all_cameras(self, lpr_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBCamera.id)).where(DBCamera.lpr_id == lpr_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBCamera).where(DBCamera.lpr_id == lpr_id).order_by(DBCamera.name.desc()).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def get_lpr_all_settings(self, lpr_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBLprSettingInstance.id)).where(DBLprSettingInstance.lpr_id == lpr_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBLprSettingInstance).where(DBLprSettingInstance.lpr_id == lpr_id).order_by(DBLprSettingInstance.name.desc()).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def add_lpr_setting(self, lpr_id: int, setting_create: LprSettingInstanceCreate):
        exists_query = await self.db_session.execute(
            select(DBLprSettingInstance)
            .where(
                DBLprSettingInstance.lpr_id == lpr_id,
                DBLprSettingInstance.name == setting_create.name
            )
        )
        if exists_query.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Setting with this name already exists for this lpr"
            )

        try:
            default_setting_query = await self.db_session.execute(
                select(DBLprSetting).where(DBLprSetting.name == setting_create.name)
            )
            default_setting = default_setting_query.scalar_one_or_none()

            setting_instance = DBLprSettingInstance(
                lpr_id=lpr_id,
                name=setting_create.name,
                description=setting_create.description,
                value=setting_create.value,
                setting_type=setting_create.setting_type,
                default_setting_id=default_setting.id if default_setting else None
            )
            self.db_session.add(setting_instance)
            await self.db_session.commit()
            await self.db_session.refresh(setting_instance)
            meilisearch_setting = LprSettingInstanceInDB.from_orm(setting_instance)
            await lpr_setting_search.sync_document(meilisearch_setting)
            return setting_instance
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not add lpr setting"
            )
        finally:
            await self.db_session.close()


    async def update_lpr_setting(self, lpr_id: int, setting_id: int, setting_update: LprSettingInstanceUpdate):
        query = await self.db_session.execute(
            select(DBLprSettingInstance)
            .where(
                DBLprSettingInstance.lpr_id == lpr_id,
                DBLprSettingInstance.id == setting_id
            )
        )
        setting_instance = query.scalar_one_or_none()
        if setting_instance is None:
            raise HTTPException(
                status_code=404, detail="Setting not found for this lpr"
            )

        try:
            update_data = setting_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(setting_instance, key, value)
            await self.db_session.commit()
            await self.db_session.refresh(setting_instance)
            meilisearch_setting = LprSettingInstanceInDB.from_orm(setting_instance)
            await lpr_setting_search.sync_document(meilisearch_setting)
            return setting_instance
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not update lpr setting"
            )
        finally:
            await self.db_session.close()

    async def remove_lpr_setting(self, lpr_id: int, setting_id: int):
        query = await self.db_session.execute(
            select(DBLprSettingInstance)
            .where(
                DBLprSettingInstance.lpr_id == lpr_id,
                DBLprSettingInstance.id == setting_id
            )
        )
        setting_instance = query.scalar_one_or_none()
        if setting_instance is None:
            raise HTTPException(
                status_code=404, detail="Setting not found for this lpr"
            )

        try:
            await self.db_session.delete(setting_instance)
            await self.db_session.commit()
            await lpr_setting_search.delete_document(setting_id)
            return {"message": f"object {setting_instance.name} deleted successfully"}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not remove lpr setting"
            )
        finally:
            await self.db_session.close()
