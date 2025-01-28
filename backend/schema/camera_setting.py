from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from schema.pagination import Pagination
from models.camera_setting import SettingType


class CameraSettingInstanceSummery(BaseModel):
    id: int
    name: str
    is_active: bool


class CameraSettingBase(BaseModel):
    name: str
    description: str
    value: str
    setting_type: SettingType = Field(default=SettingType.STRING)


class CameraSettingCreate(CameraSettingBase):
    pass


class CameraSettingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[str] = None
    setting_type: Optional[SettingType] = None
    is_active: Optional[bool] = None


class CameraSettingInDB(CameraSettingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            SettingType: lambda v: v.value
        }
        use_enum_values = True





class CameraSettingInstanceBase(BaseModel):
    name: str
    description: str
    value: str
    setting_type: SettingType = Field(default=SettingType.STRING)


class CameraSettingInstanceCreate(CameraSettingInstanceBase):
    pass


class CameraSettingInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[str] = None
    setting_type: Optional[SettingType] = None
    is_active: Optional[bool] = None


class CameraSettingInstanceInDB(CameraSettingInstanceBase):
    id: int
    camera_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


CameraSettingPagination = Pagination[CameraSettingInDB]
CameraSettingInstancePagination = Pagination[CameraSettingInstanceInDB]
