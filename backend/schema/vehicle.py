from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from models.user import UserType
from schema.pagination import Pagination


class OwnerSummary(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_type: UserType
    is_active: bool


class VehicleBase(BaseModel):
    plate_number: str
    vehicle_class: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_color: Optional[str] = None


class VehicleCreate(VehicleBase):
    owner_id: Optional[int] = None


class VehicleUpdate(BaseModel):
    pass


class VehicleInDB(VehicleBase):
    id: int
    car_image: Optional[str] = None
    car_image_url: Optional[str] = None
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


VehiclePagination = Pagination[VehicleInDB]
