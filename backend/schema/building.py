from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

from schema.pagination import Pagination
from schema.gate import GateSummmary

class BuildingBase(BaseModel):
    name: str
    latitude: str
    longitude: str
    description: Optional[str] = None


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BuildingMeilisearch(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class BuildingInDB(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    gates: Optional[List["GateSummmary"]] = []

    class Config:
        from_attributes = True


BuildingPagination = Pagination[BuildingInDB]
BuildingInDB.update_forward_refs()
