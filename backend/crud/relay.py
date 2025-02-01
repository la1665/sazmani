import math
from datetime import time
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CrudOperation
from crud.gate import GateOperation
from models.gate import DBGate
from models.relay import DBRelay
from models.key import DBRelayKey
from models.status import DBStatus
from schema.relay import RelayCreate, RelayUpdate


class RelayOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(db_session, DBRelay, None)

    async def create_relay(self, relay: RelayCreate):
        # Check if the gate exists
        db_gate = await self.db_session.execute(select(DBGate).filter(DBGate.id == relay.gate_id))
        if not db_gate.scalars().first():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Gate with the given ID does not exist.")

        # Create the relay
        try:
            new_relay = DBRelay(
                name=relay.name,
                ip=relay.ip,
                port=relay.port,
                protocol=relay.protocol,
                description=relay.description,
                number_of_keys=relay.number_of_keys,
                gate_id=relay.gate_id,
            )
            self.db_session.add(new_relay)
            await self.db_session.commit()
            await self.db_session.refresh(new_relay)

            # Initialize keys for the relay
            await self.initialize_keys(new_relay.id, new_relay.number_of_keys)
            return new_relay
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Could not create relay: {error}")
        finally:
            await self.db_session.close()


    async def initialize_keys(self, relay_id: int, number_of_keys: int):
        # Fetch the default status (e.g., "valid")
        default_status = await self.db_session.execute(select(DBStatus).filter(DBStatus.name == 'No_action'))
        db_status = default_status.scalars().first()
        if not db_status:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Default status not found.")

        # Delete existing keys for the relay
        await self.db_session.execute(delete(DBRelayKey).where(DBRelayKey.relay_id == relay_id))
        await self.db_session.commit()

        # Create new keys
        for key_number in range(1, number_of_keys + 1):
            key = DBRelayKey(
                relay_id=relay_id,
                status_id=db_status.id,
                key_number=key_number,
                duration=0,  # default duration
                description=f"Key {key_number}"
            )
            self.db_session.add(key)
        await self.db_session.commit()

    async def update_relay(self, relay_id: int, relay: RelayUpdate):
        db_relay = await self.get_one_object_id(relay_id)
        if not db_relay:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Relay not found")
        try:
            update_data = relay.dict(exclude_unset=True)
            if "gate_id" in update_data:
                gate_id = update_data["gate_id"]
                await GateOperation(self.db_session).get_one_object_id(gate_id)
                db_relay.gate_id = gate_id

            for key, value in update_data.items():
                if key != "gate_id":
                    setattr(db_relay, key, value)

            self.db_session.add(db_relay)
            await self.db_session.commit()
            await self.db_session.refresh(db_relay)
            return db_relay
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: Failed to update relay."
            )
        finally:
            await self.db_session.close()


    async def get_relays_by_gate_id(self, gate_id: int):
        """
        Retrieve all relays associated with a specific gate ID.
        """
        result = await self.db_session.execute(select(DBRelay).filter(DBRelay.gate_id == gate_id))
        return result.scalars().all()


    async def get_relay_all_keys(self, relay_id: int, page: int=1, page_size: int=10):
        total_query = await self.db_session.execute(select(func.count(DBRelayKey.id)).where(DBRelayKey.relay_id == relay_id))
        total_records = total_query.scalar_one()

        # Calculate total number of pages
        total_pages = math.ceil(total_records / page_size) if page_size else 1

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch the records
        query = await self.db_session.execute(
            select(DBRelayKey).where(DBRelayKey.relay_id == relay_id).offset(offset).limit(page_size)
        )
        objects = query.unique().scalars().all()

        return {
            "items": objects,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }
