import math
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CrudOperation
from models.building import DBBuilding
from models.gate import DBGate
from schema.building import BuildingInDB, BuildingUpdate, BuildingCreate
from search_service.search_config import building_search



class BuildingOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBBuilding, building_search)

    async def create_building(self, building:BuildingCreate):
        db_building = await self.get_one_object_name(building.name)
        if db_building:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "building already exists.")

        try:
            new_building = self.db_table(
                name=building.name,
                latitude=building.latitude,
                longitude=building.longitude,
                description=building.description
            )
            self.db_session.add(new_building)
            await self.db_session.commit()
            await self.db_session.refresh(new_building)
            meilisearch_building = BuildingInDB.from_orm(new_building)
            await building_search.sync_document(meilisearch_building)
            return new_building
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{error}: Failed to create building.")
        finally:
            await self.db_session.close()


    async def update_building(self, building_id: int, building_update: BuildingUpdate):
        db_building = await self.get_one_object_id(building_id)
        try:
            for key, value in building_update.dict(exclude_unset=True).items():
                setattr(db_building, key, value)
            self.db_session.add(db_building)
            await self.db_session.commit()
            await self.db_session.refresh(db_building)
            meilisearch_building = BuildingInDB.from_orm(db_building)
            await building_search.sync_document(meilisearch_building)
            return db_building
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update building."
            )
        finally:
            await self.db_session.close()

    async def get_building_all_gates(self, building_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBGate.id)).where(DBGate.building_id == building_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBGate).where(DBGate.building_id == building_id).order_by(DBGate.updated_at.desc()).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }
