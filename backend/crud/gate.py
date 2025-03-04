import math
from fastapi import HTTPException, status
from sqlalchemy import func, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CrudOperation
from crud.building import BuildingOperation
from models.gate import DBGate, GateType
from models.traffic import DBTraffic
from models.camera import DBCamera
from schema.gate import GateUpdate, GateCreate, GateInDB, TimeIntervalCount
from search_service.search_config import gate_search



class GateOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBGate, gate_search)

    async def create_gate(self, gate:GateCreate):
        db_gate = await self.get_one_object_name(gate.name)
        if db_gate:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "gate already exists.")
        db_building = await BuildingOperation(self.db_session).get_one_object_id(gate.building_id)
        try:
            new_gate = self.db_table(
                name=gate.name,
                gate_type=gate.gate_type,
                description=gate.description,
                building_id=db_building.id
            )
            self.db_session.add(new_gate)
            await self.db_session.commit()
            await self.db_session.refresh(new_gate)
            meilisearch_gate = GateInDB.from_orm(new_gate)
            await gate_search.sync_document(meilisearch_gate)
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
            meilisearch_gate = GateInDB.from_orm(db_gate)
            await gate_search.sync_document(meilisearch_gate)
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
            select(DBCamera).where(DBCamera.gate_id == gate_id).order_by(DBCamera.created_at.desc()).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def get_gate_traffic_stats(self, gate_type: str):
        try:
            gate_type_enum = None
            if gate_type != 'all':
                try:
                    gate_type_enum = GateType[gate_type]
                except KeyError:
                    raise HTTPException(status_code=400, detail="Invalid gate type")

            stmt = select(
                DBGate.id,
                DBGate.name,
                DBGate.gate_type,
                func.count(DBTraffic.id).label('traffic_count')
            ).select_from(DBGate).outerjoin(
                DBTraffic, DBGate.name == DBTraffic.gate_name
            )

            if gate_type_enum is not None:
                stmt = stmt.where(DBGate.gate_type == gate_type_enum)

            stmt = stmt.group_by(DBGate.id)

            result = await self.db_session.execute(stmt)
            rows = result.all()

            stats = []
            for row in rows:
                stats.append({
                    "id": row[0],
                    "name": row[1],
                    "gate_type": row[2].name,
                    "traffic_count": row[3]
                })
            return stats
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def get_gate_time_series(self, gate_id: int, interval: str):
        try:
            # Get gate first to verify existence
            gate = await self.get_one_object_id(gate_id)
            if not gate:
                raise HTTPException(status_code=404, detail="Gate not found")

            # Determine time grouping
            if interval == "daily":
                time_part = func.date_trunc('hour', DBTraffic.timestamp)
                format_str = "HH24:00"
                max_intervals = 24
            elif interval == "weekly":
                time_part = func.date_trunc('day', DBTraffic.timestamp)
                format_str = "Dy"
                max_intervals = 7
            elif interval == "monthly":
                time_part = func.date_trunc('day', DBTraffic.timestamp)
                format_str = "DD"
                max_intervals = 31
            else:
                raise HTTPException(status_code=400, detail="Invalid interval")

            # Build final query with GATE FILTER
            query = (
                select(
                    func.to_char(time_part, format_str).label('interval'),
                    func.count(DBTraffic.id).label('count')
                )
                .where(DBTraffic.gate_name == gate.name)  # Add filter here
                .group_by('interval')
            )

            # Execute query
            result = await self.db_session.execute(query)
            db_results = result.all()

            # Generate complete time series
            return self._generate_series(db_results, interval, max_intervals)

        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def _generate_series(self, db_results, interval, max_intervals):
        # Convert to case-insensitive dictionary for weekly intervals
        result_dict = {}
        for row in db_results:
            key = row.interval.upper() if interval == "weekly" else row.interval
            result_dict[key] = row.count

        # Generate complete series
        series = []
        for i in range(max_intervals):
            if interval == "daily":
                label = f"{i:02}:00-{(i+1):02}:00"
                key = f"{i:02}:00"
            elif interval == "weekly":
                days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
                label = days[i][:3].title()  # Return "Mon", "Tue" etc
                key = days[i]
            elif interval == "monthly":
                label = f"Day {i+1}"
                key = f"{i+1:02}"

            series.append(TimeIntervalCount(
                interval=label,
                count=result_dict.get(key, 0)
            ))

        return series
