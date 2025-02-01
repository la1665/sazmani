from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from models.gate import GateType
from schema.pagination import Pagination
from schema.lpr import CameraSummery



class PermittedUsersSummery(BaseModel):
    id: int
    personal_number: str
    first_name: str
    last_name: str
    class Config:
        from_attributes = True


class GateSummmary(BaseModel):
    name: str
    description: str
    class Config:
        from_attributes = True

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


class GateMeilisearch(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    gate_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
            from_attributes=True,
            json_encoders={
                datetime: lambda v: v.isoformat()
            }
        )


class GateInDB(GateBase):
    id: int
    building_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    cameras: List["CameraSummery"] = []
    permitted_users: List["PermittedUsersSummery"] = []

    class Config:
        from_attributes = True
        json_encoders = {
            GateType: lambda v: v.value
        }
        use_enum_values = True


GatePagination = Pagination[GateInDB]
GateInDB.update_forward_refs()
