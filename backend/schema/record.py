from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from schema.pagination import Pagination


class RecordBase(BaseModel):
    title: str
    timestamp: datetime


class RecordCreate(RecordBase):
    camera_id: int
    video_url: str


class RecordInDB(RecordBase):
    id: int
    camera_id: int
    video_url: str

    class Config:
        from_attributes = True


RecordPagination = Pagination[RecordBase]
RecordBase.update_forward_refs()
