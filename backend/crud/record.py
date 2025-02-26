import math
import datetime
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from crud.base import CrudOperation
from crud.camera import CameraOperation
from models.record import DBRecord, DBScheduledRecord
from models.camera import DBCamera
from schema.record import RecordCreate
from schema.schedule_record import ScheduleRecordCreate, ScheduleRecordUpdate

class RecordOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, DBRecord, None)

    async def create_record(self, record: RecordCreate):
        try:
            new_record = DBRecord(
                title=record.title,
                camera_id=record.camera_id,
                timestamp=record.timestamp,
                video_url=record.video_url
            )
            self.db_session.add(new_record)
            await self.db_session.commit()
            await self.db_session.refresh(new_record)
            return new_record
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create record.")
        finally:
            await self.db_session.close()

    async def get_all_records(self, page: int=1, page_size: int=10, camera_id: Optional[int] = None):
        try:
            query = select(DBRecord)
            if camera_id:
                query = query.where(DBRecord.camera_id == camera_id)

            total_query = await self.db_session.execute(select(func.count(self.db_table.id)).where(DBRecord.camera_id == camera_id) if camera_id else select(func.count(DBRecord.id)))
            total_records = total_query.scalar_one()

            # Calculate total number of pages
            total_pages = math.ceil(total_records / page_size) if page_size else 1

            # Calculate offset
            offset = (page - 1) * page_size

            # Apply pagination
            query = query.order_by(DBRecord.timestamp.desc()).offset(offset).limit(page_size)

            # Execute query and fetch results
            result = await self.db_session.execute(query)
            records = result.scalars().all()

            return {
                "records": records,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
            }
        except SQLAlchemyError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to retrieve records.")



class ScheduledRecordOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, DBScheduledRecord, None)

    async def create_scheduled_record(self, shedule_record: ScheduleRecordCreate):
        try:
            new_record = DBScheduledRecord(
                title=shedule_record.title,
                camera_id=shedule_record.camera_id,
                scheduled_time=shedule_record.scheduled_time,
                duration=shedule_record.duration,
                is_processed=shedule_record.is_processed
            )
            self.db_session.add(new_record)
            await self.db_session.commit()
            await self.db_session.refresh(new_record)
            return new_record
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to schedule the requested record.")
        finally:
            await self.db_session.close()


    async def get_all_scheduled_records(self, page: int=1, page_size: int=10):
        try:
            query = select(self.db_table).where(self.db_table.is_processed == False)

            total_query = await self.db_session.execute(select(func.count(self.db_table.id)).where(DBScheduledRecord.is_processed == False))
            total_records = total_query.scalar_one()

            # Calculate total number of pages
            total_pages = math.ceil(total_records / page_size) if page_size else 1

            # Calculate offset
            offset = (page - 1) * page_size

            # Apply pagination
            query = query.order_by(DBScheduledRecord.scheduled_time.desc()).offset(offset).limit(page_size)
            result = await self.db_session.execute(query)
            records = result.scalars().all()

            return {
                "records": records,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
            }
        except SQLAlchemyError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to retrieve scheduled records.")


    async def update_scheduled_record(self, record_id: int, update_data: ScheduleRecordUpdate):
        try:
            db_record = await self.get_one_object_id(record_id)
            if db_record.is_processed:
                raise HTTPException(status_code=400, detail="Cannot update a processed recording")

            # Validate camera exists if camera_id is updated
            if update_data.camera_id is not None:
                await CameraOperation(self.db_session).get_one_object_id(update_data.camera_id)
                camera = update_data.camera_id

            # Validate scheduled_time is in the future
            if update_data.scheduled_time and update_data.scheduled_time <= datetime.datetime.utcnow():
                raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(db_record, field, value)

            self.db_session.add(db_record)
            await self.db_session.commit()
            await self.db_session.refresh(db_record)
            return db_record
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to update scheduled recording.")
        finally:
            await self.db_session.close()


    async def delete_scheduled_record(self, record_id: int):
        try:
            db_record = await self.get_one_object_id(record_id)
            if db_record.is_processed:
                raise HTTPException(status_code=400, detail="Cannot delete a processed recording")

            await self.db_session.delete(db_record)
            await self.db_session.commit()
            return {"message": f"object {record_id} deleted successfully"}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Could not delete object")
        finally:
            await self.db_session.close()
