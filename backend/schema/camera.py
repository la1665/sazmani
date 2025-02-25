from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Tuple

from schema.pagination import Pagination
from schema.camera_setting import CameraSettingInstanceSummery



class LprSummery(BaseModel):
    id: int
    name: str
    is_active: bool
    class Config:
        from_attributes = True

class CameraBase(BaseModel):
    name: str
    latitude: str
    longitude: str
    description: Optional[str] = None
    crud_image: Optional[str] = None
    points: Optional[List[Tuple[int, int]]] = None



class CameraCreate(CameraBase):
    gate_id: int
    lpr_id: Optional[int] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    gate_id: Optional[int] = None
    lpr_id: Optional[int] = None
    is_active: Optional[bool] = None
    crud_image: Optional[str] = None
    points: Optional[List[Tuple[int, int]]] = None



class CameraMeilisearch(BaseModel):
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

class CameraInDB(CameraBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    gate_id: int
    settings: List[CameraSettingInstanceSummery] = []
    lpr_id: Optional[int] = None
    crud_image: Optional[str]=None
    points: Optional[List[Tuple[int, int]]] = None


    class Config:
        from_attributes = True


CameraPagination = Pagination[CameraInDB]
