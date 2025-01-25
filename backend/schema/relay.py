from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from models.relay import ProtocolEnum
from schema.pagination import Pagination


class GateSummmary(BaseModel):
    name: str
    description: str

class KeySummery(BaseModel):
    id: int
    key_number: int
    duration: Optional[int]=None
    description: Optional[str]=None
    status_id: int
    camera_id: Optional[int]=None

class RelayBase(BaseModel):
    name: str
    ip: str
    port: int
    protocol: ProtocolEnum = Field(default=ProtocolEnum.API)
    description: Optional[str] = None

class RelayCreate(RelayBase):
    gate_id: int
    number_of_keys: int


class RelayUpdate(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[ProtocolEnum] = None
    description: Optional[str] = None
    gate_id: Optional[int] = None


class RelayInDB(RelayBase):
    id: int
    # gate_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    gate_id: int
    gate: Optional[GateSummmary] = None
    keys : List[KeySummery] = []

    class Config:
        from_attributes = True


RelayPagination = Pagination[RelayInDB]
RelayInDB.update_forward_refs()
