from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# from models.user import UserType
from schema.pagination import Pagination


class TrafficBase(BaseModel):
    prefix_2: str
    alpha: str
    mid_3: str
    suffix_2: str
    plate_number: str
    ocr_accuracy: float
    vision_speed: float
    timestamp: datetime
    camera_id: int
    plate_image_path: Optional[str]
    full_image_path: Optional[str]
    # gate_id: int


class TrafficCreate(TrafficBase):
    pass

class TrafficUpdate(BaseModel):
    pass


class TrafficInDB(TrafficBase):
    id: int
    gate_id: int
    plate_image_url: Optional[str] = None
    full_image_url: Optional[str] = None
    # owner_username: Optional[str] = None
    # owner_first_name: Optional[str] = None
    # owner_last_name: Optional[str] = None

    class Config:
        from_attributes = True


TrafficPagination = Pagination[TrafficInDB]
