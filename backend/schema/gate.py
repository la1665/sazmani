from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from models.gate import GateType
from schema.pagination import Pagination
from schema.lpr import CameraSummery


class GateBase(BaseModel):
    name: str
    description: Optional[str] = None
    gate_type: GateType = Field(default=GateType.BOTH)


class GateCreate(GateBase):
    building_id: int


class GateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    building_id: Optional[int] = None
    gate_type: Optional[GateType] = None
    is_active: Optional[bool] = None


class GateInDB(GateBase):
    id: int
    building_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    cameras: List["CameraSummery"] = []
    # lprs: List["LprSummary"] = []

    class Config:
        from_attributes = True


GatePagination = Pagination[GateInDB]
GateInDB.update_forward_refs()
