from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from crud.base import CrudOperation
from models.status import DBStatus
from schema.status import StatusCreate, StatusUpdate

class StatusOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, DBStatus)

    async def create_status(self, status_create: StatusCreate):
        db_status = await self.get_one_object_name(status_create.name)
        if db_status:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "status already exists.")
        new_status = DBStatus(name=status_create.name, description=status_create.description)
        self.db_session.add(new_status)
        await self.db_session.commit()
        await self.db_session.refresh(new_status)
        return new_status

    async def update_status(self, status_id: int, status_update: StatusUpdate):
        db_status = await self.get_one_object_id(status_id)

        try:

            for key, value in status_update.dict(exclude_unset=True).items():
                setattr(db_status, key, value)

            self.db_session.add(db_status)
            await self.db_session.commit()
            await self.db_session.refresh(db_status)

            return db_status
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update status."
            )
        finally:
            await self.db_session.close()
