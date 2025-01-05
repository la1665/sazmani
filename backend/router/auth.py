from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from auth.auth import verify_password, create_access_token
from settings import settings
from database.engine import get_db
from crud.user import UserOperation
from schema.auth import Token


# Create an APIRouter for user-related routes
auth_router = APIRouter(
    prefix="/v1",
    tags=["auth"],
)


@auth_router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user_op = UserOperation(db)
    user = await user_op.get_user_personal_number(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permissions to log in to system",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.personal_number}, expires_delta=access_token_expires
    )
    return {
        "user_id": user.id,
        "user_type": user.user_type,
        "token_type": "bearer",
        "access_token": access_token,
    }
