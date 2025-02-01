from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List

from schema.gate import GateSummmary
from schema.vehicle import VehicleInDB, VehiclePagination
from schema.pagination import Pagination


class VehicleSummary(BaseModel):
    id: int
    plate_number: str
    is_active: bool
    class Config:
        from_attributes = True


class GuestBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    user_type: str = Field(default="guest")
    start_date: datetime
    end_date: datetime


class GuestCreate(GuestBase):
    inviting_user_id: int
    gate_ids: List[int] = []


# class SelfGuestUpdate(BaseModel):
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     phone_number: Optional[str] = None


class GuestUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None


# class ChangePasswordRequest(BaseModel):
#     current_password: str
#     new_password: str
#     new_password_confirm: str

# class PasswordUpdate(BaseModel):
#     hashed_password: Optional[str] = None
#     password_changed: Optional[bool] = None



class GuestMeilisearch(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    user_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    start_date: datetime
    end_date: datetime

    model_config = ConfigDict(
            from_attributes=True,
            json_encoders={
                datetime: lambda v: v.isoformat()
            }
        )


class GuestInDB(GuestBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    vehicles: List[VehicleSummary] = []
    gates: List[GateSummmary] = []

    class Config:
        from_attributes = True

        use_enum_values = True  # Add this line


GuestPagination = Pagination[GuestInDB]
