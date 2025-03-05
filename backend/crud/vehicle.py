import math
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import DBGuest, DBUser
from crud.base import CrudOperation
from crud.user import UserOperation
from models.vehicle import DBVehicle
from schema.vehicle import VehicleCreate, VehicleInDB
from settings import settings
from validator import image_validator
from image_storage.storage_management import StorageFactory
from search_service.search_config import vehicle_search


BASE_UPLOAD_DIR = Path("uploads/car_images")  # Base directory for storing images
# Ensure the directory exists
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class VehicleOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBVehicle, None)
        self.image_type = "car_images"
        self.storage = StorageFactory.get_instance(settings.STORAGE_BACKEND)

    async def get_vehicles_by_user(self, user_id: int, page: int = 1, page_size: int = 10):
        """
        Retrieve vehicles of a specific user with pagination.
        """
        offset = (page - 1) * page_size
        query = select(self.db_table).where(self.db_table.owner_id == user_id).order_by(self.db_table.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db_session.execute(query)
        items = result.scalars().all()

        # Count total records
        total_query = await self.db_session.execute(select(func.count()).where(self.db_table.owner_id == user_id))
        total_records = total_query.scalar_one()

        # Calculate total pages
        # total_pages = (total_records + page_size - 1) // page_size if page_size > 0 else 1
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        return {
            "items": items,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def get_one_vehcile_plate(self, plate: str):
        result = await self.db_session.execute(
            select(self.db_table).where(self.db_table.plate_number==plate)
        )
        object = result.unique().scalar_one_or_none()
        return object

    async def create_vehicle(self, vehicle: VehicleCreate):
        db_vehicle = await self.get_one_vehcile_plate(vehicle.plate_number)
        if db_vehicle and db_vehicle.is_active == True:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vehicle with this plate number already exists.")
        db_user_id = None
        if vehicle.owner_id:
            user_query = await self.db_session.execute(
                select(DBUser).where(DBUser.id == vehicle.owner_id)
            )
            db_user = user_query.scalar_one_or_none()
            # if db_user is None:
            #     raise HTTPException(status.HTTP_404_NOT_FOUND, f"User with ID: {vehicle.owner_id} not found!")
            if db_user:
                db_user_id = db_user.id
                count = await self._get_user_vehicle_count(vehicle.owner_id)
                if count >= db_user.max_vehicle:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST,
                        f"Maximum {db_user.max_vehicle} vehicles allowed for {db_user.personal_number}")

        db_guest_id = None
        if vehicle.guest_id:
            guest_query = await self.db_session.execute(
                select(DBGuest).where(DBGuest.id == vehicle.guest_id)
            )
            result = guest_query.scalar_one_or_none()
            # if db_user is None:
            #     raise HTTPException(status.HTTP_404_NOT_FOUND, f"User with ID: {vehicle.owner_id} not found!")
            if result:
                db_guest_id = result.id
                count = await self._get_guest_vehicle_count(vehicle.guest_id)
                if count >= result.max_vehicle:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST,
                        f"Maximum {result.max_vehicle} vehicles allowed for {result.first_name} {result.last_name}")


        try:
            new_vehicle = self.db_table(
                plate_number=vehicle.plate_number,
                vehicle_class=vehicle.vehicle_class,
                vehicle_type=vehicle.vehicle_type,
                vehicle_color=vehicle.vehicle_color,
                owner_id=db_user_id,
                guest_id=db_guest_id,
            )
            self.db_session.add(new_vehicle)
            await self.db_session.commit()
            await self.db_session.refresh(new_vehicle)
            meilisearch_data = VehicleInDB.from_orm(new_vehicle)
            await vehicle_search.sync_document(meilisearch_data)
            return new_vehicle
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create vehicle.")
        finally:
            await self.db_session.close()


    async def upload_vehicle_image(self, vehicle_id: int, car_image: UploadFile):
        vehicle = await self.get_one_object_id(vehicle_id)

        # Validate the image
        image_validator.validate_image_extension(car_image.filename)
        image_validator.validate_image_content_type(car_image.content_type)
        image_validator.validate_image_size(car_image)

        try:
            #Use ImageStorage instead of manual file handling
            saved_path = await self.storage.save_image(
                image_type=self.image_type,  # Match your corrected IMAGE_TYPES
                image_input=car_image
            )

            # Update user model
            vehicle.car_image = saved_path
            self.db_session.add(vehicle)
            await self.db_session.commit()
            await self.db_session.refresh(vehicle)
            return vehicle

        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to upload car image."
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save the car image locally: {e}"
            )
        finally:
            await self.db_session.close()


    async def delete_vehicle(self, vehicle_id: int):
            db_vehicle = await self.get_one_object_id(vehicle_id)
            try:
                db_vehicle.is_active = False
                self.db_session.add(db_vehicle)
                await self.db_session.commit()
                await self.db_session.refresh(db_vehicle)
                status_message = f"Vehicle {db_vehicle.id} deleted"
                return {"message": status_message}
            except SQLAlchemyError as error:
                await self.db_session.rollback()
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Could not delete vehicle")
            finally:
                await self.db_session.close()


    async def _get_user_vehicle_count(self, user_id: int):
        result = await self.db_session.execute(
            select(func.count(self.db_table.id)).where(self.db_table.owner_id == user_id).where(self.db_table.is_active == True)
        )
        return result.scalar()

    async def _get_guest_vehicle_count(self, guest_id: int):
        result = await self.db_session.execute(
            select(func.count(self.db_table.id)).where(self.db_table.guest_id == guest_id).where(self.db_table.is_active == True)
        )
        return result.scalar()
