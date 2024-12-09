import math
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from crud.base import CrudOperation
from crud.building import BuildingOperation
from crud.gate import GateOperation
from crud.camera import CameraOperation
from crud.user import UserOperation
from crud.vehicle import VehicleOperation
from models.traffic import DBTraffic
from schema.user import UserInDB
from schema.building import BuildingInDB
from schema.gate import GateInDB
from schema.traffic import TrafficCreate, TrafficInDB


class TrafficOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBTraffic)

    async def create_traffic(self, traffic: TrafficCreate):
        # db_vehicle = await VehicleOperation(self.db_session).get_one_vehcile_plate(traffic.plate_number)
        # db_user = await UserOperation(self.db_session).get_one_object_id(db_vehicle.owner_id) if db_vehicle and db_vehicle.owner_id else None
        db_camera = await CameraOperation(self.db_session).get_one_object_id(traffic.camera_id)
        db_gate = await GateOperation(self.db_session).get_one_object_id(db_camera.gate_id)

        try:
            naive_timestamp = traffic.timestamp.replace(tzinfo=None)
            new_traffic = self.db_table(
                plate_number = traffic.plate_number,
                ocr_accuracy = traffic.ocr_accuracy,
                vision_speed = traffic.vision_speed,
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
        query = select(self.db_table)

        # Apply filters
        if gate_id is not None:
            query = query.where(self.db_table.gate_id == gate_id)
        if camera_id is not None:
            query = query.where(self.db_table.camera_id == camera_id)
        if plate_number is not None:
            query = query.where(self.db_table.plate_number.like(f"%{plate_number}%"))
        if start_date is not None:
            query = query.where(self.db_table.timestamp >= start_date)
        if end_date is not None:
            query = query.where(self.db_table.timestamp <= end_date)

        try:
            # Get total records count with filters
            total_query = await self.db_session.execute(select(func.count()).select_from(query.subquery()))
            total_records = total_query.scalar_one()

            # Handle edge case: No records
            if total_records == 0:
                return {
                    "items": [],
                    "total_records": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size,
                }

            # Calculate total pages and offset
            total_pages = math.ceil(total_records / page_size) if page_size else 1
            offset = (page - 1) * page_size

            # Fetch paginated records
            paginated_query = query.offset(offset).limit(page_size)
            result_query = await self.db_session.execute(paginated_query)
            objects = result_query.scalars().all()

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
