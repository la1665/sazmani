from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from twisted.internet.ssl import KeyPair


from database.engine import get_db
from auth.authorization import get_admin_or_staff_user
from utils.middlewares import check_password_changed
from schema.user import UserInDB
from crud.key import KeyOperation
from schema.key import KeyCreate, KeyUpdate, KeyInDB, KeyPagination



relay_key_router = APIRouter(
    prefix="/v1/relay_keys",
    tags=["relay_keys"],
    dependencies=[Depends(check_password_changed)]
)


@relay_key_router.post("/", response_model=KeyInDB, status_code=status.HTTP_201_CREATED)
async def api_create_relay_key(
    relay_key: KeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Create a new relay key. Requires admin or staff permissions.
    """
    key_op = KeyOperation(db)
    return await key_op.create_relay_key(relay_key)

@relay_key_router.get("/", response_model=KeyPagination, status_code=status.HTTP_200_OK)
async def api_get_all_relay_keys(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    key_op = KeyOperation(db)
    return await key_op.get_all_objects(page, page_size)


@relay_key_router.get("/{key_id}", response_model=KeyInDB)
async def api_get_relay_key_by_id(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Retrieve a relay key by its ID.
    """
    key_op = KeyOperation(db)
    relay_key = await key_op.get_one_object_id(key_id)
    return relay_key


@relay_key_router.get("/by_relay/{relay_id}", response_model=List[KeyInDB])
async def api_get_keys_by_relay_id(
    relay_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Retrieve all keys associated with a relay.
    """
    key_op = KeyOperation(db)
    return await key_op.get_keys_by_relay_id(relay_id)


@relay_key_router.get("/by_camera/{camera_id}", response_model=List[KeyInDB])
async def api_get_keys_by_camera_id(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Retrieve all keys associated with a camera.
    """
    key_op = KeyOperation(db)
    return await key_op.get_keys_by_camera_id(camera_id)


@relay_key_router.get("/by_camera_and_status/", response_model=List[KeyInDB])
async def api_get_keys_by_camera_and_status(
    camera_id: int,
    status_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Retrieve all keys associated with a camera ID and a status ID.
    """
    key_op = KeyOperation(db)
    return await key_op.get_keys_by_camera_and_status(camera_id, status_id)

@relay_key_router.put("/{key_id}", response_model=KeyInDB)
async def api_update_relay_key(
    key_id: int,
    relay_key: KeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Update a relay key by its ID.
    """
    key_op = KeyOperation(db)
    updated_key = await key_op.update_relay_key(key_id, relay_key)
    return updated_key


@relay_key_router.delete("/{key_id}", response_model=KeyInDB)
async def api_delete_relay_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Delete a relay key by its ID.
    """
    key_op = KeyOperation(db)
    deleted_key = await key_op.delete_object(key_id)
    return deleted_key

@relay_key_router.patch("/{relay_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    relay_id: int,
    db: AsyncSession=Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    key_op = KeyOperation(db)
    return await key_op.change_activation_status(relay_id)



@relay_key_router.post("/{relay_key_id}/push", status_code=status.HTTP_200_OK)
async def api_push_relay_key(
    relay_key_id: int,
    command: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    """
    Simulate a push command for a relay key with a specified duration.
    """
    key_op = KeyOperation(db)
    relay_key = await key_op.get_one_object_id(relay_key_id)

    # Perform the push operation with the specified duration
    # This is a placeholder for the actual operation
    return {"message": f"Push command executed for Relay Key ID {relay_key_id} with duration {command.push_duration}"}
