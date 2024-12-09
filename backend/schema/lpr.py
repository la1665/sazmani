from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from schema.pagination import Pagination
from schema.lpr_setting import LprSettingInstanceSummery


class CameraSummery(BaseModel):
    id: int
    name: str
    is_active: bool

class LprBase(BaseModel):
    name: str
    description: str
    ip: str
    port: int
    auth_token: Optional[str] = None
    latitude: str
    longitude: str


class LprCreate(LprBase):
    pass


class LprUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    # auth_token: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_active: Optional[bool] = None



class LprInDB(LprBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: List[LprSettingInstanceSummery] = []
    cameras: List[CameraSummery]

    class Config:
        from_attributes = True


LprPagination = Pagination[LprInDB]
