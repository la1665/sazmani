from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List

from models.user import UserType
from schema.gate import GateSummmary
from schema.vehicle import VehicleInDB, VehiclePagination
from schema.pagination import Pagination


class VehicleSummary(BaseModel):
    id: int
    plate_number: str
    is_active: bool
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    personal_number: str
    national_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    office: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    user_type: UserType = Field(default=UserType.USER)


class UserCreate(UserBase):
    gate_ids: List[int] = []
    accessible_gate_ids: List[int] = []


class SelfUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    office: Optional[str] = None
    phone_number: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    office: Optional[str] = None
    phone_number: Optional[str] = None
    user_type: Optional[UserType] = None
    is_active: Optional[bool] = None
    password_changed: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str

class PasswordUpdate(BaseModel):
    hashed_password: Optional[str] = None
    password_changed: Optional[bool] = None



class UserMeilisearch(BaseModel):
    id: int
    personal_number: str
    national_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    user_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
            from_attributes=True,
            json_encoders={
                datetime: lambda v: v.isoformat()
            }
        )


class UserInDB(UserBase):
    id: int
    profile_image: Optional[str] = None
    profile_image_url: Optional[str] = None
    password_changed: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    vehicles: List[VehicleSummary] = []
    gates: List[GateSummmary] = []
    accessible_gates: List[GateSummmary] = []

    class Config:
        from_attributes = True
        json_encoders = {
            UserType: lambda v: v.value  # Serialize enum to string
        }
        use_enum_values = True  # Add this line


UserPagination = Pagination[UserInDB]
