import math
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from tcp.tcp_manager import add_connection, update_connection
from crud.base import CrudOperation
from crud.gate import GateOperation
from crud.lpr import LprOperation
from models.camera_setting import DBCameraSetting, DBCameraSettingInstance
from models.camera import DBCamera
from schema.camera import CameraUpdate, CameraCreate
from schema.camera_setting import CameraSettingInstanceUpdate, CameraSettingInstanceCreate



class CameraOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBCamera)

    async def create_camera(self, camera: CameraCreate):
        db_camera = await self.get_one_object_name(camera.name)
        if db_camera:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "camera already exists.")
        db_gate = await GateOperation(self.db_session).get_one_object_id(camera.gate_id)
        db_lpr = await LprOperation(self.db_session).get_one_object_id(camera.lpr_id)
        try:
            new_camera = DBCamera(
                name=camera.name,
                latitude=camera.latitude,
                longitude=camera.longitude,
                description=camera.description,
                gate_id=db_gate.id,
                lpr_id=db_lpr.id
            )

            self.db_session.add(new_camera)
            await self.db_session.flush()

            query = await self.db_session.execute(select(DBCameraSetting))
            default_settings = query.unique().scalars().all()
            for setting in default_settings:
                setting_instance = DBCameraSettingInstance(
                    camera_id=new_camera.id,
                    name=setting.name,
                    description=setting.description,
                    value=setting.value,
                    setting_type=setting.setting_type,
                    is_active=setting.is_active,
                    default_setting_id=setting.id
                )
                self.db_session.add(setting_instance)

            await self.db_session.commit()
            await self.db_session.refresh(new_camera)

            return new_camera
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create camera.")
        finally:
            await self.db_session.close()


    async def update_camera(self, camera_id: int, camera_update: CameraUpdate):
        db_camera = await self.get_one_object_id(camera_id)
        try:
            update_data = camera_update.dict(exclude_unset=True)
            if "gate_id" in update_data:
                gate_id = update_data.pop("gate_id", None)
                await GateOperation(self.db_session).get_one_object_id(gate_id)
                db_camera.gate_id = gate_id

            if "lpr_id" in update_data:
                lpr_id = update_data.pop("lpr_id", None)
                await LprOperation(self.db_session).get_one_object_id(lpr_id)
                db_camera.lpr_id = lpr_id

            for key, value in update_data.items():
                setattr(db_camera, key, value)

            self.db_session.add(db_camera)
            await self.db_session.commit()
            await self.db_session.refresh(db_camera)

            return db_camera
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update camera."
            )
        finally:
            await self.db_session.close()

    async def get_camera_all_settings(self, camera_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBCameraSettingInstance.id)).where(DBCameraSettingInstance.camera_id == camera_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBCameraSettingInstance).where(DBCameraSettingInstance.camera_id == camera_id).order_by(DBCameraSettingInstance.id).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def add_camera_setting(self, camera_id: int, setting_create: CameraSettingInstanceCreate):
        exists_query = await self.db_session.execute(
            select(DBCameraSettingInstance)
            .where(
                DBCameraSettingInstance.camera_id == camera_id,
                DBCameraSettingInstance.name == setting_create.name
            )
        )
        if exists_query.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Setting with this name already exists for this camera"
            )

        try:
            default_setting_query = await self.db_session.execute(
                select(DBCameraSetting).where(DBCameraSetting.name == setting_create.name)
            )
            default_setting = default_setting_query.scalar_one_or_none()

            setting_instance = DBCameraSettingInstance(
                camera_id=camera_id,
                name=setting_create.name,
                description=setting_create.description,
                value=setting_create.value,
                setting_type=setting_create.setting_type,
                default_setting_id=default_setting.id if default_setting else None
            )
            self.db_session.add(setting_instance)
            await self.db_session.commit()
            await self.db_session.refresh(setting_instance)
            return setting_instance
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not add camera setting"
            )
        finally:
            await self.db_session.close()


    async def update_camera_setting(self, camera_id: int, setting_id: int, setting_update: CameraSettingInstanceUpdate):
        query = await self.db_session.execute(
            select(DBCameraSettingInstance)
            .where(
                DBCameraSettingInstance.camera_id == camera_id,
                DBCameraSettingInstance.id == setting_id
            )
        )
        setting_instance = query.scalar_one_or_none()
        if setting_instance is None:
            raise HTTPException(
                status_code=404, detail="Setting not found for this camera"
            )

        try:
            update_data = setting_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(setting_instance, key, value)
            await self.db_session.commit()
            await self.db_session.refresh(setting_instance)
            return setting_instance
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not update camera setting"
            )
        finally:
            await self.db_session.close()

    async def remove_camera_setting(self, camera_id: int, setting_id: int):
        query = await self.db_session.execute(
            select(DBCameraSettingInstance)
            .where(
                DBCameraSettingInstance.camera_id == camera_id,
                DBCameraSettingInstance.id == setting_id
            )
        )
        setting_instance = query.scalar_one_or_none()
        if setting_instance is None:
            raise HTTPException(
                status_code=404, detail="Setting not found for this camera"
            )

        try:
            await self.db_session.delete(setting_instance)
            await self.db_session.commit()
            return {"message": f"object {setting_instance.name} deleted successfully"}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{error}: Could not remove camera setting"
            )
        finally:
            await self.db_session.close()
