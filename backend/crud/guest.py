import os
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from auth.auth import get_password_hash
from crud.base import CrudOperation
from models.user import DBUser, DBGuest
from models.gate import DBGate
from schema.guest import GuestMeilisearch, GuestUpdate, GuestCreate
from search_service.search_config import guest_search




class GuestOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBGuest)

    # async def get_user_personal_number(self, personal_number: str):
    #     query = await self.db_session.execute(select(self.db_table).filter(self.db_table.personal_number == personal_number))
    #     user = query.unique().scalar_one_or_none()
    #     return user

    async def create_guest(self, guest:GuestCreate):
        # hashed_password = get_password_hash(guest.national_id)
        # query = await self.db_session.execute(
        #     select(self.db_table).where(
        #         self.db_table.personal_number == guest.personal_number)
        #     )
        # db_guest = query.unique().scalar_one_or_none()
        # if db_guest:
        #     raise HTTPException(status.HTTP_400_BAD_REQUEST, "guest with this cridentials already exists.")

        # Fetch accessible gates

        accessible_query = await self.db_session.execute(
            select(DBUser).where(DBUser.id == guest.inviting_user_id))
        db_user = accessible_query.scalar_one_or_none()
        if not db_user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "guest must have an invitation from an active user.")

        db_accessible_gates = []
        if guest.gate_ids:
            accessible_query = await self.db_session.execute(
                select(DBGate).where(DBGate.id.in_(guest.gate_ids))
            )
            db_accessible_gates = accessible_query.scalars().all()

        try:
            new_guest = self.db_table(
                first_name=guest.first_name,
                last_name=guest.last_name,
                phone_number=guest.phone_number,
                start_date=guest.start_date,
                end_date=guest.end_date,
                user_type="guest",
                inviting_user=db_user,
                gates=db_accessible_gates,
            )

            self.db_session.add(new_guest)
            await self.db_session.commit()
            await self.db_session.refresh(new_guest)
            meilisearch_data = GuestMeilisearch(
                    id=new_guest.id,
                    first_name=new_guest.first_name,
                    last_name=new_guest.last_name,
                    phone_number=new_guest.phone_number,
                    user_type=new_guest.user_type,  # Convert enum to string
                    is_active=new_guest.is_active,
                    created_at=new_guest.created_at.isoformat(),
                    updated_at=new_guest.updated_at.isoformat(),
                    start_date=new_guest.start_date.isoformat(),
                    end_date=new_guest.end_date.isoformat(),
                )
            await guest_search.sync_document(meilisearch_data)
            return new_guest

        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create guest.")

        finally:
                await self.db_session.close()


    async def update_guest(self, guest_id: int, guest_update: GuestUpdate):
        db_guest = await self.get_one_object_id(guest_id)
        try:
            for key, value in guest_update.dict(exclude_unset=True).items():
                setattr(db_guest, key, value)
            self.db_session.add(db_guest)
            await self.db_session.commit()
            await self.db_session.refresh(db_guest)
            meilisearch_data = GuestMeilisearch(
                id=db_guest.id,
                first_name=db_guest.first_name,
                last_name=db_guest.last_name,
                phone_number=db_guest.phone_number,
                user_type=db_guest.user_type,  # Convert enum to string
                is_active=db_guest.is_active,
                created_at=db_guest.created_at.isoformat(),
                updated_at=db_guest.updated_at.isoformat(),
                start_date=db_guest.start_date.isoformat(),
                end_date=db_guest.end_date.isoformat(),
            )
            await guest_search.sync_document(meilisearch_data)
            return db_guest
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update guest."
            )
        finally:
            await self.db_session.close()

    # async def update_password(self, guest_id: int, password_update: PasswordUpdate):
    #     db_guest = await self.get_one_object_id(guest_id)
    #     try:
    #         for key, value in password_update.dict(exclude_unset=True).items():
    #             setattr(db_guest, key, value)
    #         self.db_session.add(db_guest)
    #         await self.db_session.commit()
    #         await self.db_session.refresh(db_guest)
    #         return db_guest
    #     except SQLAlchemyError as error:
    #         await self.db_session.rollback()
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"{error}: Failed to update guest."
    #         )
    #     finally:
    #         await self.db_session.close()
