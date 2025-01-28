from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from urllib.parse import unquote

from auth.authorization import get_current_active_user
from search_service.search_config import user_search, building_search, gate_search, camera_search, lpr_search, traffic_search
from schema.user import UserInDB
from schema.building import BuildingInDB
from schema.gate import GateInDB
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
    limit: int = Query(10, gt=0, le=100),
    offset: int = 0,
    nocache: bool = Query(False),
    current_user: UserInDB=Depends(get_current_active_user)
):

    service_map = {
        "users": user_search,
        "buildings": building_search,
        "gates": gate_search,
        "cameras": camera_search,
        "lprs": lpr_search,
        "traffics": traffic_search,
    }

    if model not in service_map:
        raise HTTPException(404, "Model not searchable")

    if nocache:
            await redis_cache.invalidate_model(model)

    return await service_map[model].search(
        query=query,
        filters=filters,
        limit=limit,
        offset=offset
    )
