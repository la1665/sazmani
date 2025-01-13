from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError

from settings import settings
from database.engine import get_db
from auth.auth import oauth2_scheme
from schema.auth import TokenData
from schema.user import UserInDB
from models.user import DBUser, UserType
from models.camera import DBCamera
from crud.user import UserOperation



async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    try:
        if settings.SECRET_KEY and settings.ALGORITHM:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            personal_number = payload.get("sub")
            if personal_number is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization Error: Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"})
            token_data = TokenData(personal_number=personal_number)
            user_op = UserOperation(db)
            current_user = await user_op.get_user_personal_number(personal_number=token_data.personal_number)
            if current_user is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization Error: Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"})
            return current_user

    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization Error: Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"})


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"Permission denied":"Inactive user"}
        )
    return current_user


async def get_admin_user(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.user_type is not UserType.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
            {"Permission denied":"Admin access required"})
    return current_user


async def get_admin_or_staff_user(current_user: DBUser = Depends(get_current_active_user)):
    if current_user.user_type not in [UserType.ADMIN, UserType.STAFF]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"Permission denied":"Admin or staff access required"}
        )
    return current_user


async def get_admin_staff_viewer_user(
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
    camera_id: int = None,
):
    # Check if the user type is valid
    if current_user.user_type not in [UserType.ADMIN, UserType.STAFF, UserType.VIEWER]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"Permission denied": "Not accessible for this user type"},
        )

    # If the user is a viewer, check gate access
    if current_user.user_type == UserType.VIEWER and camera_id is not None:
        # Fetch the camera and its associated gate
        query = await db.execute(
            select(DBCamera)
            .where(DBCamera.id == camera_id)
            .options(selectinload(DBCamera.gate))  # Load the associated gate
        )
        camera = query.scalars().first()

        if not camera:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                {"Error": "Camera not found"},
            )

        # Check if the user's gates include the gate associated with the camera
        if camera.gate.id not in [gate.id for gate in current_user.gates]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                {"Permission denied": "Access to this camera is denied"},
            )

    return current_user


async def get_self_or_admin_user(
    user_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    if current_user.user_type == UserType.ADMIN or current_user.id == user_id:
        return current_user
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        {"Permission denied":"Access denied"}
    )

async def get_self_or_admin_or_staff_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    user_op = UserOperation(db)
    target_user = await user_op.get_one_object_id(user_id)

    if current_user.user_type == UserType.ADMIN:
        # Admin has access to update any user
        return target_user

    if current_user.user_type == UserType.STAFF:
        # Staff can update users with 'viewer' or 'user' types
        if target_user.user_type in [UserType.VIEWER, UserType.USER]:
            return target_user

    if current_user.id == user_id:
        # Users can update their own profile
        return target_user

    # If none of the conditions are met, deny access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied: You cannot view this resource.",
    )


async def get_self_user_only(
    user_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    if current_user.id == user_id:
        return current_user
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        {"permission denied":"Access denied: You can only access your own data."}
    )
