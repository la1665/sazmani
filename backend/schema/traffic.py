from pydantic import BaseModel, ConfigDict
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
    plate_image: Optional[str]
    full_image: Optional[str]


class TrafficCreate(TrafficBase):
    camera_id: int

class TrafficUpdate(BaseModel):
    pass



class TrafficMeilisearch(BaseModel):
    id: int
    prefix_2: str
    alpha: str
    mid_3: str
    suffix_2: str
    plate_number: str
    gate_name: Optional[str] = None
    camera_name: Optional[str] = None
    timestamp: datetime
    access_granted: bool

    model_config = ConfigDict(
            from_attributes=True,
            json_encoders={
                datetime: lambda v: v.isoformat()
            }
        )


class DeleteTrafficResponse(BaseModel):
    message: str
    deleted_count: int
    image_errors: list[str] = []


class TrafficInDB(TrafficBase):
    id: int
    gate_name: str
    camera_name: str
    plate_image_url: Optional[str] = None
    full_image_url: Optional[str] = None
    access_granted: bool

    class Config:
        from_attributes = True


TrafficPagination = Pagination[TrafficInDB]
