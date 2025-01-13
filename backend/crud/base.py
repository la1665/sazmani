import math
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class CrudOperation:
    def __init__(self, db_session: AsyncSession, db_table) -> None:
        self.db_session = db_session
        self.db_table = db_table

    async def get_one_object_id(self, object_id: int):
        result = await self.db_session.execute(
            select(self.db_table).where(self.db_table.id==object_id)
        )
        object = result.unique().scalar_one_or_none()
        if object is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{object_id} not found in {self.db_table}!")
        return object

    async def get_one_object_name(self, object_name: str):
        result = await self.db_session.execute(
            select(self.db_table).where(self.db_table.name==object_name)
        )
        object = result.unique().scalar_one_or_none()
        return object

    async def get_all_objects(self, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(self.db_table.id)))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(self.db_table).order_by(self.db_table.id).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }


    async def change_activation_status(self, object_id: int):
        db_object = await self.get_one_object_id(object_id)
        try:
            # Toggle the activation status
            db_object.is_active = not db_object.is_active

            # Add the object to the session and commit
            # async with self.db_session.begin():  # Begin a transaction
            self.db_session.add(db_object)
            await self.db_session.commit()
            await self.db_session.refresh(db_object)
            # Return the appropriate message
            status_message = "activated" if db_object.is_active else "deactivated"
            return {"message": status_message}

        except SQLAlchemyError as error:
            await self.db_session.rollback()  # Rollback on error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Could not change activation status",
            )
        finally:
            await self.db_session.close()

    async def delete_object(self, object_id: int):
        db_object = await self.get_one_object_id(object_id)
        try:
            await self.db_session.delete(db_object)
            await self.db_session.commit()
            # return db_object
            return {"message": f"object {object_id} deleted successfully"}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Could not delete object")
        finally:
            await self.db_session.close()
