from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# from models.user import UserType
from schema.building import BuildingInDB
from schema.gate import GateInDB
from schema.pagination import Pagination
from schema.user import UserInDB


class TrafficBase(BaseModel):
    plate_number: str
    ocr_accuracy: float
    vision_speed: float
    timestamp: datetime
    camera_id: int
    # gate_id: int


class TrafficCreate(TrafficBase):
    pass


class TrafficUpdate(BaseModel):
    pass


class TrafficInDB(TrafficBase):
    id: int
    gate_id: int
    # owner_username: Optional[str] = None
    # owner_first_name: Optional[str] = None
    # owner_last_name: Optional[str] = None

    class Config:
        from_attributes = True


TrafficPagination = Pagination[TrafficInDB]
