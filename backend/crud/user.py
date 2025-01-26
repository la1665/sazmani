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
from models.user import DBUser, UserType
from models.gate import DBGate
from schema.user import UserUpdate, UserCreate, PasswordUpdate, SelfUserUpdate
from validator import image_validator
from image_storage.storage_management import StorageFactory


BASE_UPLOAD_DIR = Path("uploads/profile_images")  # Base directory for storing images
# Ensure the directory exists
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UserOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBUser)
        self.image_type = "profile_images"
        self.storage = StorageFactory.get_instance()

    async def get_user_personal_number(self, personal_number: str):
        query = await self.db_session.execute(select(self.db_table).filter(self.db_table.personal_number == personal_number))
        user = query.unique().scalar_one_or_none()
        return user

    async def create_user(self, user:UserCreate):
        hashed_password = get_password_hash(user.national_id)
        query = await self.db_session.execute(
            select(self.db_table).where(
                or_(self.db_table.personal_number == user.personal_number, self.db_table.email == user.email)
            ))
        db_user = query.unique().scalar_one_or_none()
        if db_user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "user with this cridentials already exists.")

        db_gates = []
        if user.gate_ids:
            gates_query = await self.db_session.execute(
                select(DBGate).where(DBGate.id.in_(user.gate_ids))
            )
            db_gates = gates_query.scalars().all()

        try:
            new_user = self.db_table(
                personal_number=user.personal_number,
                national_id=user.national_id,
                first_name=user.first_name,
                last_name=user.last_name,
                office=user.office,
                phone_number=user.phone_number,
                email=user.email,
                user_type=user.user_type,
                hashed_password=hashed_password,
                gates=db_gates,
                password_changed=(user.user_type == UserType.ADMIN),
            )

            self.db_session.add(new_user)
            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            return new_user

        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create user.")

        finally:
                await self.db_session.close()


    async def update_user(self, user_id: int, user_update: UserUpdate|SelfUserUpdate):
        db_user = await self.get_one_object_id(user_id)
        try:
            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            self.db_session.add(db_user)
            await self.db_session.commit()
            await self.db_session.refresh(db_user)
            return db_user
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update user."
            )
        finally:
            await self.db_session.close()

    async def update_password(self, user_id: int, password_update: PasswordUpdate):
        db_user = await self.get_one_object_id(user_id)
        try:
            for key, value in password_update.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            self.db_session.add(db_user)
            await self.db_session.commit()
            await self.db_session.refresh(db_user)
            return db_user
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update user."
            )
        finally:
            await self.db_session.close()


    async def delete_user(self, user_id: int):
        db_user = await self.get_one_object_id(user_id)
        try:
            db_user.is_active = False
            self.db_session.add(db_user)
            await self.db_session.commit()
            await self.db_session.refresh(db_user)
            status_message = f"User {db_user.id} deleted"
            return {"message": status_message}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Could not delete user")
        finally:
            await self.db_session.close()


    async def upload_user_profile_image(self, user_id: int, profile_image: UploadFile):
        user = await self.get_one_object_id(user_id)

        # Validate the image
        image_validator.validate_image_extension(profile_image.filename)
        image_validator.validate_image_content_type(profile_image.content_type)
        image_validator.validate_image_size(profile_image)

        try:
            #Use ImageStorage instead of manual file handling
            saved_path = await self.storage.save_image(
                image_type=self.image_type,  # Match your corrected IMAGE_TYPES
                image_input=profile_image
            )

            # Update user model
            user.profile_image = saved_path
            self.db_session.add(user)
            await self.db_session.commit()
            await self.db_session.refresh(user)
            return user


        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to upload profile image."
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save the profile image locally: {e}"
            )
        finally:
            await self.db_session.close()
