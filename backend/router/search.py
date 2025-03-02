from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from urllib.parse import unquote

from auth.authorization import get_current_active_user
from search_service.search_config import (
    user_search, guest_search,
    building_search, gate_search,
    camera_search, camera_setting_search,
    lpr_search, lpr_setting_search,
    traffic_search, vehicle_search,
)
from schema.user import UserInDB
from redis_cache import redis_cache
from utils.middlewares import check_password_changed

search_router = APIRouter(
    prefix="/v1/search",
    tags=["search"]
)

@search_router.get("/{model}", dependencies=[Depends(check_password_changed)])
async def model_search(
    model: str,
    query: str = Query(..., min_length=1),
    filters: Optional[str] = None,
    page: int = Query(1, gt=0),  # Added page parameter
    page_size: int = Query(10, gt=0, le=100),  # Renamed from limit to page_size for clarity
    nocache: bool = Query(False),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Search models with pagination.
    """
    service_map = {
        "users": user_search,
        "guests": guest_search,
        "vehicles": vehicle_search,
        "buildings": building_search,
        "gates": gate_search,
        "cameras": camera_search,
        "camera_settings": camera_setting_search,
        "lprs": lpr_search,
        "lpr_settings": lpr_setting_search,
        "traffics": traffic_search,
    }

    if model not in service_map:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not searchable")

    if nocache:
        await redis_cache.invalidate_model(model)

    # Calculate offset from page number
    offset = (page - 1) * page_size

    # Perform search
    search_result = await service_map[model].search(
        query=query,
        filters=filters,
        limit=page_size,
        offset=offset
    )

    # Prepare pagination metadata
    total_items = search_result.get("total", 0)
    total_pages = (total_items + page_size - 1) // page_size  # Ceiling division for total pages

    return {
        "items": search_result.get("items", []),
        "total_records": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
    }
