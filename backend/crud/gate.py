import math
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CrudOperation
from crud.building import BuildingOperation
from models.gate import DBGate
from models.camera import DBCamera
from schema.gate import GateUpdate, GateCreate




class GateOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBGate)

    async def create_gate(self, gate:GateCreate):
        db_gate = await self.get_one_object_name(gate.name)
        if db_gate:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "gate already exists.")
        db_building = await BuildingOperation(self.db_session).get_one_object_id(gate.building_id)
        try:
            new_gate = DBGate(
                name=gate.name,
                gate_type=gate.gate_type,
                description=gate.description,
                building_id=db_building.id
            )
            self.db_session.add(new_gate)
            await self.db_session.commit()
            await self.db_session.refresh(new_gate)
            return new_gate
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create gate.")
        finally:
            await self.db_session.close()


    async def update_gate(self, gate_id: int, gate_update: GateUpdate):
        db_gate = await self.get_one_object_id(gate_id)
        try:
            update_data = gate_update.dict(exclude_unset=True)
            if "building_id" in update_data:
                building_id = update_data["building_id"]
                await BuildingOperation(self.db_session).get_one_object_id(building_id)
                db_gate.building_id = building_id

            for key, value in update_data.items():
                if key != "building_id":
                    setattr(db_gate, key, value)
            self.db_session.add(db_gate)
            await self.db_session.commit()
            await self.db_session.refresh(db_gate)
            return db_gate
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update gate."
            )
        finally:
            await self.db_session.close()



    async def get_gate_all_cameras(self, gate_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBCamera.id)).where(DBCamera.gate_id == gate_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBCamera).where(DBCamera.gate_id == gate_id).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }
