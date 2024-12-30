from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from minio.error import S3Error
from datetime import timedelta

from settings import settings
from database.engine import get_db
# from database.minio_engine import minio_client
from schema.user import UserCreate, UserPagination, UserUpdate, UserInDB, ChangePasswordRequest
from crud.user import UserOperation
from auth.auth import verify_password, get_password_hash
from auth.authorization import get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only
from utils.middlewwares import check_password_changed


# Define the base URL for serving uploaded files
BASE_UPLOAD_URL = "/uploads/profile_images"

# Create an APIRouter for user-related routes
user_router = APIRouter(
    prefix="/v1/users",
    tags=["users"],
)


@user_router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def api_create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_user)
):
    """
    Create a new user.
    """
    user_op = UserOperation(db)
    return await user_op.create_user(user)


@user_router.get("/{user_id}", response_model=UserInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_user)
):
    """
    Retrieve a user by ID.
    """
    user_op = UserOperation(db)
    user = await user_op.get_one_object_id(user_id)

    # Generate the profile image URL if the image exists
    if user.profile_image:
        filename = Path(user.profile_image).name
        user.profile_image_url = f"{request.base_url}uploads/profile_images/{filename}"


    # return UserInDB(
    #     **user.__dict__,
    #     profile_image_url=image_url
    # )
    return user


@user_router.get("/",response_model=UserPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_users(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_user)
):
    """
    Retrieve all users with pagination.
    """
    user_op = UserOperation(db)
    result = await user_op.get_all_objects(page, page_size)
    for user in result["items"]:
        if user.profile_image:
            filename = Path(user.profile_image).name
            user.profile_image_url = f"{request.base_url}uploads/profile_images/{filename}"

    return result


@user_router.put("/{user_id}", response_model=UserInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_self_or_admin_user)
):
    """
    Update an existing user.
    """
    user_op = UserOperation(db)
    return await user_op.update_user(user_id, user_update)


@user_router.delete("/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_user)
):
    """
    Delete a user by ID.
    """
    user_op = UserOperation(db)
    return await user_op.delete_user(user_id)


@user_router.post("/change-password", status_code=status.HTTP_200_OK)
async def api_change_password(
    change_request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_self_or_admin_user)
):
    """
    Allow users to change their password.
    """
    user_op = UserOperation(db)

    # Verify current password
    if not verify_password(change_request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    # Update password
    hashed_new_password = get_password_hash(change_request.new_password)
    await user_op.update_user(
        current_user.id,
        UserUpdate(hashed_password=hashed_new_password, password_changed=True),
    )

    return {"message": "Password changed successfully"}



@user_router.post("/{user_id}/profile-image", response_model=UserInDB, dependencies=[Depends(check_password_changed)])
async def api_upload_profile_image(
    user_id: int,
    profile_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_self_or_admin_user)
):
    """
    Upload or update the user's profile image.
    """
    user_op = UserOperation(db)
    return await user_op.upload_user_profile_image(user_id, profile_image)


# @user_router.get("/{user_id}/profile-image", response_class=StreamingResponse, dependencies=[Depends(check_password_changed)])
# async def api_get_profile_image(
#     user_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: UserInDB = Depends(get_current_active_user)
# ):
#     """
#     Fetch and serve the user's profile image from MinIO.
#     Accessible by all authenticated and active users.
#     """
#     user_op = UserOperation(db)
#     user = await user_op.get_one_object_id(user_id)
#     if not user or not user.profile_image:
#         raise HTTPException(status_code=404, detail="Profile image not found.")

#     try:
#         response = minio_client.get_object(settings.MINIO_PROFILE_IMAGE_BUCKET, user.profile_image)
#         return StreamingResponse(response, media_type="image/jpeg")  # Adjust media_type as needed
#     except S3Error as e:
#         print(f"Error fetching image: {e}")
#         raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Failed to fetch profile image: {e}.")
