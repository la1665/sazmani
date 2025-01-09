from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List

from models.user import UserType
from schema.gate import GateBase
from schema.vehicle import VehicleInDB, VehiclePagination, VehicleSummary
from schema.pagination import Pagination


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


class UserInDB(UserBase):
    id: int
    profile_image: Optional[str] = None
    profile_image_url: Optional[str] = None
    password_changed: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    vehicles: List[VehicleSummary] = []
    gates: List[GateBase] = []

    class Config:
        from_attributes = True


UserPagination = Pagination[UserInDB]
