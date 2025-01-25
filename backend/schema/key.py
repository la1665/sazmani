from datetime import datetime
from pydantic import BaseModel, Field
from datetime import time
from typing import Optional

from models.relay import ProtocolEnum
from schema.lpr import CameraSummery
from schema.pagination import Pagination

class RelaySummery(BaseModel):
    id: int
    name: str
    protocol: ProtocolEnum
    is_active: bool

class StatusSummery(BaseModel):
    id: int
    name: str
    is_active: bool


class KeyBase(BaseModel):
    key_number: int
    duration: Optional[int]=None
    description: Optional[str]=None


class KeyCreate(KeyBase):
    relay_id: int
    status_id: int
    camera_id: Optional[int]=None


class KeyUpdate(BaseModel):
    key_number: Optional[int]=None
    duration: Optional[int]=None
    description: Optional[str]=None
    status_id: Optional[int]=None
    camera_id: Optional[int]=None


class KeyInDB(KeyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    relay: Optional[RelaySummery] = None
    camera: Optional[CameraSummery] = None
    status: Optional[StatusSummery] = None


    class Config:
        from_attributes = True


KeyPagination = Pagination[KeyInDB]
KeyInDB.update_forward_refs()
