from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from utils.middlewares import security_middleware
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
    username = form_data.username

    #Check if the user is locked
    if await security_middleware.is_locked(username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    user_op = UserOperation(db)
    user = await user_op.get_user_personal_number(username)

    # ❌ Incorrect credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        failed_attempts = await security_middleware.track_failed_login(username)

        #Lock user if too many failed attempts
        if failed_attempts >= security_middleware.max_failed_attempts:
            await security_middleware.lock_user(username)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. You are locked out.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password. {security_middleware.max_failed_attempts - failed_attempts} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    #Reset failed attempts on successful login
    await security_middleware.redis.delete(f"security:failed_attempts:{username}")

    # Generate access token
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
