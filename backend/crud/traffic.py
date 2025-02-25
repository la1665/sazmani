import base64
import math
import os
from pathlib import Path
from typing import List
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
from schema.traffic import TrafficCreate, TrafficInDB
from search_service.search_config import traffic_search
from utils.vehicle_access import VehicleAccessChecker

BASE_UPLOAD_DIR = Path("uploads/plate_images")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TRAFFIC_UPLOAD_DIR = Path("uploads/traffic_images")
TRAFFIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TrafficOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBTraffic, traffic_search)

    async def get_one_plate_number(self, plate_number: str):
        result = await self.db_session.execute(
            select(self.db_table).where(self.db_table.plate_number==plate_number)
        )
        object = result.unique().scalar_one_or_none()
        return object

    async def create_traffic(self, traffic: TrafficCreate):
        db_camera = await CameraOperation(self.db_session).get_one_object_id(traffic.camera_id)
        db_gate = await GateOperation(self.db_session).get_one_object_id(db_camera.gate_id)

        try:
            plate_image = None
            if traffic.plate_image:
                try:
                    plate_image = traffic.plate_image
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to save plate image: {e}"
                    )
            full_image = None
            if traffic.full_image:
                try:
                    full_image = traffic.full_image
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to save traffic image: {e}"
                    )
            naive_timestamp = traffic.timestamp.replace(tzinfo=None)

            # Check if the vehicle's owner has access to the gate
            access_checker = VehicleAccessChecker(self.db_session)
            is_accessible, db_vehicle, db_owner = await access_checker.is_vehicle_allowed(
                traffic.plate_number, db_gate.id
            )

            new_traffic = self.db_table(
                prefix_2 = traffic.prefix_2,
                alpha = traffic.alpha,
                mid_3 = traffic.mid_3,
                suffix_2 = traffic.suffix_2,
                plate_number = traffic.plate_number,
                ocr_accuracy = traffic.ocr_accuracy,
                vision_speed = traffic.vision_speed,
                plate_image=plate_image,
                full_image=full_image,
                timestamp = naive_timestamp,
                camera_name = db_camera.name,
                gate_name = db_gate.name,
                access_granted = is_accessible,
            )
            self.db_session.add(new_traffic)
            await self.db_session.commit()
            await self.db_session.refresh(new_traffic)
            meilisearch_traffic = TrafficInDB.from_orm(new_traffic)
            await traffic_search.sync_document(meilisearch_traffic)
            return new_traffic
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create traffic.")
        finally:
            await self.db_session.close()



    async def get_all_traffics(
        self,
        page: int = 1,
        page_size: int = 10,
        gate_id: int = None,
        camera_id: int = None,
        prefix_2: str = None,
        alpha: str = None,
        mid_3: str = None,
        suffix_2: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ):
        """
        Retrieve all traffic data with optional filters for gate_id, camera_id, plate_number, and date range, with pagination.
        """
        try:
            if camera_id is not None:
                db_camera = await CameraOperation(self.db_session).get_one_object_id(camera_id)
                camera_name = db_camera.name
            if gate_id is not None:
                db_gate = await GateOperation(self.db_session).get_one_object_id(gate_id)
                gate_name = db_gate.name
            # Base query
            query = select(self.db_table).order_by(self.db_table.timestamp.desc())

            # Apply filters
            if gate_id is not None:
                query = query.where(self.db_table.gate_name == gate_name)
            if camera_id is not None:
                query = query.where(self.db_table.camera_name == camera_name)
            if prefix_2 is not None:
                query = query.where(self.db_table.prefix_2.like(f"%{prefix_2}%"))
            if alpha is not None:
                query = query.where(self.db_table.alpha == alpha)
            if mid_3 is not None:
                query = query.where(self.db_table.mid_3.like(f"%{mid_3}%"))
            if suffix_2 is not None:
                query = query.where(self.db_table.suffix_2.like(f"%{suffix_2}%"))
            # if plate_number is not None:
            #     query = query.where(self.db_table.plate_number.ilike(f"%{plate_number}%"))
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


    async def get_traffics_by_camera_and_date(
        self,
        start_date: datetime,
        end_date: datetime,
        camera_id: int=None
    ):
        if camera_id:
            # Get camera details
            camera = await CameraOperation(self.db_session).get_one_object_id(camera_id)
            result = await self.db_session.execute(
                select(self.db_table).where(
                    self.db_table.camera_name == camera.name,
                    self.db_table.timestamp >= start_date,
                    self.db_table.timestamp < end_date
                )
            )
        else:
            result = await self.db_session.execute(
                select(self.db_table).where(
                    self.db_table.timestamp >= start_date,
                    self.db_table.timestamp < end_date
                )
            )
        return result.scalars().all()

    async def delete_traffic_batch(self, traffics):
        try:
            for traffic in traffics:
                await self.db_session.delete(traffic)
            await self.db_session.commit()
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Delete failed: {error}")
