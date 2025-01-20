from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database.engine import get_db
from crud.status import StatusOperation
from schema.status import StatusCreate, StatusUpdate, StatusInDB, StatusPagination
from auth.authorization import get_admin_or_staff_user
from utils.middlewwares import check_password_changed
from schema.user import UserInDB


status_router = APIRouter(
    prefix="/v1/status",
    tags=["status"],
    dependencies=[Depends(check_password_changed)]
)

@status_router.post("/", response_model=StatusInDB, status_code=status.HTTP_201_CREATED)
async def create_status(
    status: StatusCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    status_crud = StatusOperation(db)
    return await status_crud.create_status(status)

@status_router.get("/{status_id}", response_model=StatusInDB)
async def read_status(
    status_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    status_crud = StatusOperation(db)
    status = await status_crud.get_one_object_id(status_id)
    return status

@status_router.put("/{status_id}", response_model=StatusInDB)
async def update_status(
    status_id: int,
    status: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    status_crud = StatusOperation(db)
    updated_status = await status_crud.update_status(status_id, status)
    return updated_status

@status_router.delete("/{status_id}", response_model=StatusInDB)
async def delete_status(
    status_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    status_crud = StatusOperation(db)
    deleted_status = await status_crud.delete_object(status_id)
    return deleted_status

@status_router.get("/", response_model=StatusPagination)
async def read_all_status(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user)
):
    status_crud = StatusOperation(db)
    return await status_crud.get_all_objects(page, page_size)
