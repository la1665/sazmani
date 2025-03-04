import os
import pandas as pd
from io import BytesIO
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
from schema.user import UserInDB, UserUpdate, UserCreate, PasswordUpdate, SelfUserUpdate
from settings import settings
from validator import image_validator
from image_storage.storage_management import StorageFactory
from search_service.search_config import user_search


BASE_UPLOAD_DIR = Path("uploads/profile_images")  # Base directory for storing images
# Ensure the directory exists
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UserOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBUser, user_search)
        self.image_type = "profile_images"
        self.storage = StorageFactory.get_instance(settings.STORAGE_BACKEND)

    async def get_user_personal_number(self, personal_number: str):
        query = await self.db_session.execute(select(self.db_table).filter(self.db_table.personal_number == personal_number))
        user = query.unique().scalar_one_or_none()
        return user

    async def create_user(self, user:UserCreate):
        hashed_password = get_password_hash(user.national_id)
        if user.email is None:
            query = await self.db_session.execute(
                select(self.db_table).where(
                    self.db_table.personal_number == user.personal_number
                ))
        else:
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

        # Fetch accessible gates
        db_accessible_gates = []
        if user.accessible_gate_ids:
            accessible_query = await self.db_session.execute(
                select(DBGate).where(DBGate.id.in_(user.accessible_gate_ids))
            )
            db_accessible_gates = accessible_query.scalars().all()

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
                accessible_gates=db_accessible_gates,
                password_changed=(user.user_type == UserType.ADMIN),
            )

            self.db_session.add(new_user)
            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            meilisearch_data = UserInDB.from_orm(new_user)
            await user_search.sync_document(meilisearch_data)
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
            meilisearch_data = UserInDB.from_orm(db_user)
            await user_search.sync_document(meilisearch_data)
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

    async def create_users_from_excel(self, file: UploadFile):
        try:
            contents = await file.read()
            df = pd.read_excel(BytesIO(contents)).replace({pd.NA: None, '': None})

            required_columns = {'personal_number', 'national_id', 'user_type'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                  f"Missing mandatory columns: {', '.join(missing)}")

            users_to_create = []
            skipped_users = 0

            for _, row in df.iterrows():
                if pd.isna(row.get("personal_number")) or pd.isna(row.get("national_id")):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                        "personal_number and national_id cannot be empty")

                user_type = self._parse_user_type(row.get("user_type"))

                user_data = {
                    "personal_number":str(row["personal_number"]),
                    "national_id":str(row["national_id"]),
                    "first_name":row.get("first_name"),
                    "last_name":row.get("last_name"),
                    "office":row.get("office"),
                    "phone_number":self._parse_phone_number(row.get("phone_number")),
                    "email":row.get("email"),
                    "user_type":user_type,
                    "gates":self._process_id_list(row.get("gate_ids")),
                    "accessible_gates":self._process_id_list(row.get("accessible_gate_ids")),
                    "hashed_password": get_password_hash(str(row["national_id"])),
                }

               # Check for existing user
                query = await self.db_session.execute(
                    select(self.db_table).where(
                        or_(self.db_table.personal_number == user_data["personal_number"],
                            self.db_table.email == user_data["email"]) if user_data["email"] else
                        (self.db_table.personal_number == user_data["personal_number"])
                    )
                )
                db_user = query.scalar_one_or_none()
                if db_user:
                    skipped_users += 1
                    print(f"Skipping existing user: {user_data['personal_number']}")
                    continue
                    # raise HTTPException(status.HTTP_400_BAD_REQUEST, "user with this cridentials already exists.")

                gates = []
                if user_data["gates"]:
                    gates_query = await self.db_session.execute(
                        select(DBGate).where(DBGate.id.in_(user_data["gate_ids"]))
                    )
                    gates = gates_query.scalars().all()

                # Fetch accessible gates
                accessible_gates = []
                if user_data["accessible_gates"]:
                    accessible_query = await self.db_session.execute(
                        select(DBGate).where(DBGate.id.in_(user_data["accessible_gates"]))
                    )
                    accessible_gates = accessible_query.scalars().all()

                # Now assign correct values
                new_user = DBUser(
                    personal_number=user_data["personal_number"],
                    national_id=user_data["national_id"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    office=user_data["office"],
                    phone_number=user_data["phone_number"],
                    email=user_data["email"],
                    user_type=user_data["user_type"],
                    gates=gates,  # Correct: Assigning DBGate objects
                    accessible_gates=accessible_gates,  # Correct: Assigning DBGate objects
                    hashed_password=user_data["hashed_password"],
                )

                users_to_create.append(new_user)

            if users_to_create:
                self.db_session.add_all(users_to_create)
                await self.db_session.commit()
            return {"message": f"{len(users_to_create)} users created successfully"}

        except pd.errors.EmptyDataError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty Excel file")

        except SQLAlchemyError as e:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Database error: {str(e)}")

        except Exception as e:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                              f"Error processing Excel file: {str(e)}")

    def _parse_user_type(self, value):
        try:
            return UserType(str(value).lower()) if value else UserType.USER
        except ValueError:
            return UserType.USER


    def _parse_phone_number(self, value):
        if pd.isna(value) or value is None:
            return None
        return str(int(value))  # Remove decimal if it's a float


    def _process_id_list(self, value):
        if pd.isna(value) or value in [None, ""]:
            return []
        try:
            return [int(x.strip()) for x in str(value).split(",")]
        except ValueError:
            return []
