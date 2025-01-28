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
    ADMIN_PERSONAL_NUMBER: Optional[str] = None
    ADMIN_NATIONAL_ID: Optional[str] = None
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_FIRST_NAME: Optional[str] = None
    ADMIN_LAST_NAME: Optional[str] = None
    ADMIN_OFFICE: Optional[str] = None
    ADMIN_PHONE_NUMBER: Optional[str] = None
    AUTH_TOKEN: Optional[str] = None
    HMAC_SECRET_KEY: Optional[str] = None
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_USE_SSL: bool=True
    MINIO_PROFILE_IMAGE_BUCKET: Optional[str] = None
    MINIO_FULL_IMAGE_BUCKET: Optional[str] = None
    MINIO_PLATE_IMAGE_BUCKET: Optional[str] = None
    CLIENT_KEY_PATH: Optional[str] = None
    CLIENT_CERT_PATH: Optional[str] = None
    CA_CERT_PATH: Optional[str] = None
    LPR_AUTH_TOKEN: Optional[str] = None
    NATS_CA_PATH: str
    NATS_CERT_PATH: str
    NATS_KEY_PATH: str
    NATS_USER: str
    NATS_PASS: str
    NAT_SERVER: str
    TLS_HOSTNAME: str
    BASE_UPLOAD_DIR: str
    STORAGE_BACKEND: str
    MINIO_BUCKET_PREFIX: str
    IMAGE_TYPES: str
    HIGH_VOLUME_IMAGE_TYPES: str
    IMAGE_NAME_PREFIX: str
    MEILI_URL: str
    MEILI_MASTER_KEY: str
    REDIS_URL: str
    CACHE_TTL: int


    class Config:
        env_file = "backend/.env"


settings = Settings()
