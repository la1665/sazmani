import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.record import DBRecord

class RecordOperation:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_record(self, title: str, camera_id: int, timestamp: datetime.datetime, video_url: str):
        record = DBRecord(title=title, camera_id=camera_id, timestamp=timestamp, video_url=video_url)
        self.session.add(record)
        await self.session.commit()
        return record

    async def get_records(self, camera_id: int = None):
        query = select(DBRecord)
        if camera_id:
            query = query.where(DBRecord.camera_id == camera_id)
        result = await self.session.execute(query)
        return result.scalars().all()
