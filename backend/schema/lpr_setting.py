from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from schema.pagination import Pagination
from models.lpr_setting import LprSettingType


class LprSettingInstanceSummery(BaseModel):
    id: int
    name: str
    is_active: bool


class LprSettingBase(BaseModel):
    name: str
    description: str
    value: str
    setting_type: LprSettingType = Field(default=LprSettingType.STRING)


class LprSettingCreate(LprSettingBase):
    pass


class LprSettingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[str] = None
    setting_type: Optional[LprSettingType] = None
    is_active: Optional[bool] = None


class LprSettingInDB(LprSettingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            LprSettingType: lambda v: v.value  # Serialize enum to string
        }
        use_enum_values = True  # Add this line


class LprSettingInstanceBase(BaseModel):
    name: str
    description: str
    value: str
    setting_type: LprSettingType = Field(default=LprSettingType.STRING)


class LprSettingInstanceCreate(LprSettingInstanceBase):
    pass


class LprSettingInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[str] = None
    setting_type: Optional[LprSettingType] = None
    is_active: Optional[bool] = None


class LprSettingInstanceInDB(LprSettingInstanceBase):
    id: int
    lpr_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


LprSettingPagination = Pagination[LprSettingInDB]
LprSettingInstancePagination = Pagination[LprSettingInstanceInDB]
