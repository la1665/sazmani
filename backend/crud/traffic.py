import base64
import math
import os
from pathlib import Path
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from crud.base import CrudOperation
from crud.gate import GateOperation
from crud.camera import CameraOperation
from models.traffic import DBTraffic
from schema.traffic import TrafficCreate


BASE_UPLOAD_DIR = Path("uploads/plate_images")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TrafficOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBTraffic)

    async def get_one_plate_number(self, plate_number: str):
        result = await self.db_session.execute(
            select(self.db_table).where(self.db_table.plate_number==plate_number)
        )
        object = result.unique().scalar_one_or_none()
        return object

    async def create_traffic(self, traffic: TrafficCreate):
        # db_vehicle = await VehicleOperation(self.db_session).get_one_vehcile_plate(traffic.plate_number)
        # db_user = await UserOperation(self.db_session).get_one_object_id(db_vehicle.owner_id) if db_vehicle and db_vehicle.owner_id else None
        db_camera = await CameraOperation(self.db_session).get_one_object_id(traffic.camera_id)
        db_gate = await GateOperation(self.db_session).get_one_object_id(db_camera.gate_id)

        try:
            plate_image_path = None
            if traffic.plate_image_path:
                try:
                    # Decode the base64 image and save it to the file system
                    image_bytes = base64.b64decode(traffic.plate_image_path)
                    image_name = f"{traffic.plate_number}_{traffic.timestamp.isoformat().replace(':', '-')}.jpg"
                    image_path = BASE_UPLOAD_DIR / image_name
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    plate_image_path = str(image_path)
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to save plate image: {e}"
                    )
            naive_timestamp = traffic.timestamp.replace(tzinfo=None)
            new_traffic = self.db_table(
                plate_number = traffic.plate_number,
                ocr_accuracy = traffic.ocr_accuracy,
                vision_speed = traffic.vision_speed,
                plate_image_path=plate_image_path,
                timestamp = naive_timestamp,
                camera_id = db_camera.id,
                gate_id = db_gate.id,
            )
            self.db_session.add(new_traffic)
            await self.db_session.commit()
            await self.db_session.refresh(new_traffic)

            return new_traffic
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create traffic.")
        finally:
            await self.db_session.close()


        # return TrafficInDB(
        #     **new_traffic.__dict__,
        #     owner_username=db_user.username if db_user else None,
        #     owner_first_name=db_user.first_name if db_user else None,
        #     owner_last_name=db_user.last_name if db_user else None,
        # )

    async def get_all_traffics(
        self,
        page: int = 1,
        page_size: int = 10,
        gate_id: int = None,
        camera_id: int = None,
        plate_number: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ):
        """
        Retrieve all traffic data with optional filters for gate_id, camera_id, plate_number, and date range, with pagination.
        """
        try:
            # Base query
            query = select(self.db_table).order_by(self.db_table.id)

            # Apply filters
            if gate_id is not None:
                query = query.where(self.db_table.gate_id == gate_id)
            if camera_id is not None:
                query = query.where(self.db_table.camera_id == camera_id)
            if plate_number is not None:
                query = query.where(self.db_table.plate_number.ilike(f"%{plate_number}%"))
            if start_date is not None:
                query = query.where(self.db_table.timestamp >= start_date)
            if end_date is not None:
                query = query.where(self.db_table.timestamp <= end_date)

            # Total records query
            total_query = await self.db_session.execute(select(func.count()).select_from(query.subquery()))
            total_records = total_query.scalar_one()

            # Handle no results
            if total_records == 0:
                return {
                    "items": [],
                    "total_records": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size,
                }

            # Calculate pagination
            total_pages = math.ceil(total_records / page_size) if page_size else 1
            offset = (page - 1) * page_size if page_size else None

            # Paginated query
            if page_size:
                query = query.offset(offset).limit(page_size)

            # Fetch results
            result_query = await self.db_session.execute(query)
            objects = result_query.scalars().all()

            # Return response
            return {
                "items": objects,
                "total_records": total_records,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size,
            }

        except Exception as e:
            print(f"[ERROR] Failed to fetch traffic data: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch traffic data.")
