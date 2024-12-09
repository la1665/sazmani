from pydantic import BaseModel
from typing import TypeVar, Generic, List


T = TypeVar('T')
class Pagination(BaseModel, Generic[T]):
    items: List[T]
    total_records: int
    total_pages: int
    current_page: int
    page_size: int

    class Config:
        from_attributes = True
