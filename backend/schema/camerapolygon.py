from pydantic import BaseModel
from typing import List, Tuple, Optional


class CameraPolygonBase(BaseModel):
    points: List[Tuple[int, int]]  # A list of tuples where each tuple is (x, y) pixel coordinates

class CameraPolygonCreate(CameraPolygonBase):
    camera_id: int  # The camera ID associated with this polygon

class CameraPolygonUpdate(CameraPolygonBase):
    pass  # You may want to add specific fields for updates, if needed

class CameraPolygonInDB(BaseModel):
    camera_id: int
    crud_image: Optional[str]=None
    polygon_points: Optional[List[Tuple[int, int]]] = None # List of tuples (x, y)

    class Config:
        orm_mode = True
