from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from schema.pagination import Pagination

class StatusBase(BaseModel):
    name: str
    description: Optional[str] = None

class StatusCreate(StatusBase):
    pass

class StatusUpdate(StatusBase):
    pass


class StatusInDB(StatusBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



StatusPagination = Pagination[StatusInDB]
StatusInDB.update_forward_refs()
