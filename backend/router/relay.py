from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

from auth.authorization import get_admin_or_staff_user
from database.engine import get_db
from crud.relay import RelayOperation
from schema.user import UserInDB
from schema.relay import RelayCreate, RelayPagination, RelayUpdate, RelayInDB
from schema.key import KeyPagination
from utils.middlewwares import check_password_changed


relay_router = APIRouter(
    prefix="/v1/relays",
    tags=["relays"],
)

@relay_router.post("/", response_model=RelayInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_relay(
    relay: RelayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Create a new relay.
    Only accessible by admins or staff.
    """
    relay_op = RelayOperation(db)
    return await relay_op.create_relay(relay)


@relay_router.get("/", response_model=RelayPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_relays(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    relay_op = RelayOperation(db)
    return await relay_op.get_all_objects(page, page_size)


@relay_router.get("/{relay_id}", response_model=RelayInDB, dependencies=[Depends(check_password_changed)])
async def api_get_relay(
    relay_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Fetch a relay by its unique ID.
    """
    relay_op = RelayOperation(db)
    relay = await relay_op.get_one_object_id(relay_id)
    return relay


@relay_router.get("/gate/{gate_id}", dependencies=[Depends(check_password_changed)])
async def api_get_relays_by_gate_id(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Fetch relays by gate ID.
    """
    relay_op = RelayOperation(db)
    relays = await relay_op.get_relays_by_gate_id(gate_id)
    return relays


@relay_router.put("/{relay_id}", response_model=RelayInDB, dependencies=[Depends(check_password_changed)])
async def api_update_relay(
    relay_id: int,
    relay: RelayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Update an existing relay by ID.
    """
    relay_op = RelayOperation(db)
    updated_relay = await relay_op.update_relay(relay_id, relay)
    return updated_relay


@relay_router.delete("/{relay_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_relay(
    relay_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Delete a relay by its ID.
    """
    relay_op = RelayOperation(db)
    return await relay_op.delete_object(relay_id)

@relay_router.patch("/{relay_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    relay_id: int,
    db: AsyncSession=Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    relay_op = RelayOperation(db)
    return await relay_op.change_activation_status(relay_id)

@relay_router.get("/{relay_id}/keys", response_model=KeyPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_gate_all_cameras(relay_id: int, page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    gate_op = RelayOperation(db)
    return await gate_op.get_relay_all_keys(relay_id, page, page_size)
