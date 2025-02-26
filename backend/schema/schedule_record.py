from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from schema.pagination import Pagination


class ScheduleRecordBase(BaseModel):
    title: str
    is_processed: bool = Field(default=False)


class ScheduleRecordCreate(ScheduleRecordBase):
    camera_id: int
    duration: int
    scheduled_time: datetime


class ScheduleRecordUpdate(BaseModel):
    title: Optional[str] = None
    camera_id: Optional[int] = None
    scheduled_time: Optional[datetime] = None
    duration: Optional[int] = None


class ScheduleRecordInDB(ScheduleRecordBase):
    id: int
    camera_id: int
    duration: int
    scheduled_time: datetime

    class Config:
        from_attributes = True


ScheduleRecordPagination = Pagination[ScheduleRecordBase]
ScheduleRecordBase.update_forward_refs()
