from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from minio.error import S3Error
from datetime import timedelta

from settings import settings
from database.engine import get_db
# from database.minio_engine import minio_client
from schema.user import UserInDB
from schema.guest import GuestCreate, GuestPagination, GuestUpdate, GuestInDB
from crud.guest import GuestOperation
from auth.auth import verify_password, get_password_hash
from auth.authorization import get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only
from utils.middlewares import check_password_changed


# Define the base URL for serving uploaded files

# Create an APIRouter for user-related routes
guest_router = APIRouter(
    prefix="/v1/guests",
    tags=["guests"],
)


@guest_router.post("/", response_model=GuestInDB, status_code=status.HTTP_201_CREATED)
async def api_create_guest(
    guest: GuestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Create a new user.
    """
    guest_op = GuestOperation(db)
    return await guest_op.create_guest(guest)


@guest_router.get("/{guest_id}", response_model=GuestInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_guest(
    request: Request,
    guest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_or_staff_user)
):
    """
    Retrieve a user by ID.
    """
    guest_op = GuestOperation(db)
    return await guest_op.get_one_object_id(guest_id)



@guest_router.get("/",response_model=GuestPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_guest(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Retrieve all users with pagination.
    """
    guest_op = GuestOperation(db)
    result = await guest_op.get_all_objects(page, page_size)

    return result


@guest_router.put("/{guest_id}", response_model=GuestInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_guest_by_admin(
    guest_id: int,
    guest_update: GuestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Update an existing user.
    """
    guest_op = GuestOperation(db)
    return await guest_op.update_guest(guest_id, guest_update)


# @guest_router.put("/profile/{guest_id}", response_model=GuestInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
# async def api_update_user(
#     guest_id: int,
#     guest_update: SelfGuestUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user: UserInDB=Depends(get_self_user_only)
# ):
#     """
#     Update an existing user.
#     """
#     guest_op = GuestOperation(db)
#     return await guest_op.update_guest(guest_id, guest_update)


@guest_router.delete("/{guest_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_guest(
    guest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Delete a user by ID.
    """
    guest_op = GuestOperation(db)
    return await guest_op.delete_object(guest_id)


# @guest_router.post("/{guest_id}/change-password", status_code=status.HTTP_200_OK)
# async def api_change_password(
#     guest_id: int,
#     change_request: ChangePasswordRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: UserInDB = Depends(get_self_or_admin_or_staff_user)
# ):
#     """
#     Allow users to change their password.
#     """
#     guest_op = GuestOperation(db)
#     target_user = await guest_op.get_one_object_id(guest_id)

#     # Verify current password is same
#     if change_request.new_password != change_request.new_password_confirm:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password confirmation error")

#     # Verify current password
#     if not verify_password(change_request.current_password, target_user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

#     # Update password
#     hashed_new_password = get_password_hash(change_request.new_password)
#     await guest_op.update_password(
#         target_user.id,
#         PasswordUpdate(hashed_password=hashed_new_password, password_changed=True),
#     )

#     return {"message": "Password changed successfully"}
