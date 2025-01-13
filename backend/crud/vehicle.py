from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import DBUser
from crud.base import CrudOperation
from crud.user import UserOperation
from models.vehicle import DBVehicle
from schema.vehicle import VehicleCreate
from validator import image_validator

BASE_UPLOAD_DIR = Path("uploads/car_images")  # Base directory for storing images
# Ensure the directory exists
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



class VehicleOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBVehicle)

    async def get_vehicles_by_user(self, user_id: int, page: int = 1, page_size: int = 10):
        """
        Retrieve vehicles of a specific user with pagination.
        """
        offset = (page - 1) * page_size
        query = select(self.db_table).where(self.db_table.owner_id == user_id).offset(offset).limit(page_size)
        result = await self.db_session.execute(query)
        items = result.scalars().all()

        total_query = await self.db_session.execute(select(func.count()).where(self.db_table.owner_id == user_id))
        total_records = total_query.scalar()

        return {
            "items": items,
            "total_records": total_records,
            "page": page,
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
        if db_vehicle:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "vehicle with this plate number already exists.")
        user_id = None
        if vehicle.owner_id:
            user_query = await self.db_session.execute(
                select(DBUser).where(DBUser.id == vehicle.owner_id)
            )
            db_user = user_query.scalar_one_or_none()
            if db_user is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"User with ID: {vehicle.owner_id} not found!")
            user_id = db_user.id
            # db_user = await UserOperation(self.db_session).get_one_object_id(vehicle.owner_id)
        try:
            new_vehicle = self.db_table(
                plate_number=vehicle.plate_number,
                vehicle_class=vehicle.vehicle_class,
                vehicle_type=vehicle.vehicle_type,
                vehicle_color=vehicle.vehicle_color,
                owner_id=user_id,
            )
            self.db_session.add(new_vehicle)
            await self.db_session.commit()
            await self.db_session.refresh(new_vehicle)
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

        # Generate a unique filename
        unique_filename = f"{vehicle.plate_number}_{vehicle.id}_{car_image.filename}"
        file_path = BASE_UPLOAD_DIR / unique_filename

        # Save the file locally
        try:
            with open(file_path, "wb") as f:
                file_data = await car_image.read()
                f.write(file_data)

            # Update the car's image path
            vehicle.car_image = str(file_path)
            vehicle.car_image_url = str(file_path)
            # Save changes to the database
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
