from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# from models.user import UserType
from schema.pagination import Pagination

class VehicleBase(BaseModel):
    plate_number: str
    vehicle_class: str
    vehicle_type: str
    vehicle_color: str


class VehicleCreate(VehicleBase):
    owner_id: Optional[int] = None


class VehicleUpdate(BaseModel):
    pass


class VehicleInDB(VehicleBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class VehicleSummary(BaseModel):
    id: int
    plate_number: str


VehiclePagination = Pagination[VehicleInDB]
