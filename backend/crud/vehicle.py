from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CrudOperation
from crud.user import UserOperation
from models.vehicle import DBVehicle
from schema.vehicle import VehicleCreate


class VehicleOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBVehicle)

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
        if vehicle.owner_id:
            db_user = await UserOperation(self.db_session).get_one_object_id(vehicle.owner_id)
        try:
            new_vehicle = self.db_table(
                plate_number=vehicle.plate_number,
                vehicle_class=vehicle.vehicle_class,
                vehicle_type=vehicle.vehicle_type,
                vehicle_color=vehicle.vehicle_color,
                owner_id=db_user.id,
            )
            self.db_session.add(new_vehicle)
            await self.db_session.commit()
            await self.db_session.refresh(new_vehicle)
            return new_vehicle
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create vehicle.")
