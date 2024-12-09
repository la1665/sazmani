from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int=5432
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int=120
    ALGORITHM: Optional[str] = None
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_EMAIL: Optional[str] = None
    AUTH_TOKEN: Optional[str] = None
    HMAC_SECRET_KEY: Optional[str] = None
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_USE_SSL: bool=True
    MINIO_PROFILE_IMAGE_BUCKET: Optional[str] = None
    MINIO_FULL_IMAGE_BUCKET: Optional[str] = None
    MINIO_PLATE_IMAGE_BUCKET: Optional[str] = None
    CLIENT_KEY_PATH: str
    CLIENT_CERT_PATH: str
    CA_CERT_PATH: str
    LPR_AUTH_TOKEN: str


    class Config:
        env_file = "./backend/.env"


settings = Settings()
