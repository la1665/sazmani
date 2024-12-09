from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from datetime import datetime, timedelta

from settings import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(plain_password: str) -> str|None:
    return pwd_context.hash(plain_password)


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    if not settings.SECRET_KEY or not settings.ALGORITHM:
        raise ValueError("SECRET_KEY and ALGORITHM must be set in the settings.")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
