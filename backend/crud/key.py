from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from crud.base import CrudOperation
from crud.camera import CameraOperation
from crud.status import StatusOperation
from models.relay import DBRelay
from models.key import DBRelayKey
from models.status import DBStatus
from schema.key import KeyCreate, KeyUpdate


class KeyOperation(CrudOperation):
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, DBRelayKey, None)

    async def create_relay_key(self, relay_key: KeyCreate):
        """
        Create a new relay key.
        """
        try:
            if relay_key.camera_id:
                db_camera = await CameraOperation(self.db_session).get_one_object_id(relay_key.camera_id)
            # Validate if the relay exists
            db_relay = await self.db_session.execute(select(DBRelay).filter(DBRelay.id == relay_key.relay_id))
            if not db_relay.scalars().first():
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Relay ID does not exist.")

            # Validate if the status exists
            db_status = await self.db_session.execute(select(DBStatus).filter(DBStatus.id == relay_key.status_id))
            if not db_status.scalars().first():
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Status ID does not exist.")

            # Create the relay key
            db_relay_key = DBRelayKey(
                key_number=relay_key.key_number,
                duration=relay_key.key_number,
                description=relay_key.key_number,
                relay_id=relay_key.relay_id,
                status_id=relay_key.status_id,
                camera_id=relay_key.camera_id,
            )
            self.db_session.add(db_relay_key)
            await self.db_session.commit()
            await self.db_session.refresh(db_relay_key)
            return db_relay_key
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Could not create relay key: {error}")
        except Exception as e:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"An error occurred during creation of relay key: {str(e)}")
        finally:
            await self.db_session.close()

    async def get_keys_by_relay_id(self, relay_id: int):
        """
        Retrieve all keys associated with a relay ID.
        """
        result = await self.db_session.execute(select(DBRelayKey).filter(DBRelayKey.relay_id == relay_id).order_by(DBRelayKey.updated_at.desc()))
        return result.scalars().all()

    async def get_keys_by_camera_id(self, camera_id: int):
        """
        Retrieve all keys associated with a camera ID.
        """
        result = await self.db_session.execute(select(DBRelayKey).filter(DBRelayKey.camera_id == camera_id).order_by(DBRelayKey.updated_at.desc()))
        return result.scalars().all()

    async def get_keys_by_camera_and_status(self, camera_id: int, status_id: int):
        """
        Retrieve all keys associated with a specific camera ID and status ID.
        """
        result = await self.db_session.execute(
            select(DBRelayKey).filter(
                DBRelayKey.camera_id == camera_id,
                DBRelayKey.status_id == status_id
            ).order_by(DBRelayKey.updated_at.desc())
        )
        return result.scalars().all()

    async def update_relay_key(self, key_id: int, relay_key: KeyUpdate):
        """
        Update an existing relay key.
        """
        db_relay_key = await self.get_one_object_id(key_id)
        if not db_relay_key:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Relay key not found.")

        try:
            update_data = relay_key.dict(exclude_unset=True)
            if "status_id" in update_data:
                status_id = update_data["status_id"]
                await StatusOperation(self.db_session).get_one_object_id(status_id)
                db_relay_key.status_id = status_id
            if "camera_id" in update_data:
                camera_id = update_data["camera_id"]
                await CameraOperation(self.db_session).get_one_object_id(camera_id)
                db_relay_key.camera_id = camera_id

            for key, value in update_data.items():
                if key not in ["camera_id", "status_id"]:
                    setattr(db_relay_key, key, value)
            await self.db_session.commit()
            await self.db_session.refresh(db_relay_key)
            return db_relay_key
        except SQLAlchemyError as error:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Could not perform updating relay key: {error}")
        except Exception as e:
            await self.db_session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"An error occurred: {str(e)}")
        finally:
            await self.db_session.close()
