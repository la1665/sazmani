import os
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import get_password_hash
from crud.base import CrudOperation
from models.user import DBUser, UserType
from schema.user import UserUpdate, UserCreate
from validator import profile_image_validator
# from utils.minio_utils import upload_profile_image

BASE_UPLOAD_DIR = Path("uploads/profile_images")  # Base directory for storing images

# Ensure the directory exists
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class UserOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBUser)

    async def get_user_username(self, username: str):
        query = await self.db_session.execute(select(self.db_table).filter(self.db_table.username == username))
        user = query.unique().scalar_one_or_none()
        return user

    async def create_user(self, user:UserCreate):
        hashed_password = get_password_hash(user.password)
        query = await self.db_session.execute(
            select(self.db_table).where(
                or_(self.db_table.username == user.username, self.db_table.email == user.email)
            ))
        db_user = query.unique().scalar_one_or_none()
        if db_user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "username/email already exists.")

        try:
            new_user = self.db_table(
                username=user.username,
                email=user.email,
                user_type=user.user_type,
                hashed_password=hashed_password,
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


    async def update_user(self, user_id: int, user_update: UserUpdate):
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


    async def delete_user(self, user_id: int):
        db_user = await self.get_one_object_id(user_id)
        try:
            db_user.isactive = not db_user.is_active
            self.db_session.add(db_user)
            await self.db_session.commit()
            await self.db_session.refresh(db_user)
            status_message = "activated" if db_user.is_active else "deactivated"
            return {"message": status_message}
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Could not delete user")
        finally:
            await self.db_session.close()



    # async def upload_profile_image(self, user_id: int, profile_image: UploadFile):

    #     user = await self.get_one_object_id(user_id)
    #     # Validate the image
    #     profile_image_validator.validate_image_extension(profile_image.filename)
    #     profile_image_validator.validate_image_content_type(profile_image.content_type)
    #     profile_image_validator.validate_image_size(profile_image)

    #     # Read the file data
    #     file_data = await profile_image.read()

    #     # Delete old profile image if exists
    #     # if user.profile_image:
    #     #     old_filename = user.profile_image.split("/")[-1].split("?")[0]
    #     #     delete_profile_image(old_filename)

    #     # Upload new profile image
    #     unique_filename = upload_profile_image(
    #         file_data=file_data,
    #         user_id=user.id,
    #         username=user.username,
    #         original_filename=profile_image.filename,
    #         content_type=profile_image.content_type
    #     )
    #     user.profile_image = unique_filename

    #     try:
    #         # async with self.db_session as session:
    #             self.db_session.add(user)
    #             await self.db_session.commit()
    #             await self.db_session.refresh(user)
    #             return user
    #     except SQLAlchemyError as error:
    #         await self.db_session.rollback()
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"{error}: Failed to upload profile image."
    #         )

    async def upload_user_profile_image(self, user_id: int, profile_image: UploadFile):
        user = await self.get_one_object_id(user_id)

        # Validate the image
        profile_image_validator.validate_image_extension(profile_image.filename)
        profile_image_validator.validate_image_content_type(profile_image.content_type)
        profile_image_validator.validate_image_size(profile_image)

        # Generate a unique filename
        unique_filename = f"{user.username}_{user.id}_{profile_image.filename}"
        file_path = BASE_UPLOAD_DIR / unique_filename

        # Save the file locally
        try:
            with open(file_path, "wb") as f:
                file_data = await profile_image.read()
                f.write(file_data)

            # Update the user's profile image path
            user.profile_image = str(file_path)
            user.profile_image_url = str(file_path)
            # Save changes to the database
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
