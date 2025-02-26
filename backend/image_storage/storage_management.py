import datetime
import uuid
from pathlib import Path
from starlette.datastructures import UploadFile as StarletteUploadFile
import numpy as np
import cv2
import logging
import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from minio import Minio, S3Error
import os
from settings import settings
from fastapi import UploadFile

import os
import logging
from minio import Minio
import io



class MinioClientSingleton:
    _client = None

    @staticmethod
    def get_instance():
        if MinioClientSingleton._client is None:
            try:
                # Load configuration from environment variables
                minio_endpoint = settings.MINIO_ENDPOINT
                minio_access_key = settings.MINIO_ACCESS_KEY
                minio_secret_key = settings.MINIO_SECRET_KEY
                secure = settings.MINIO_USE_SSL

                # Validate required environment variables
                if not minio_endpoint or not minio_access_key or not minio_secret_key:
                    raise ValueError("Missing required MinIO configuration: ENDPOINT, ACCESS_KEY, or SECRET_KEY.")

                # Initialize MinIO client
                MinioClientSingleton._client = Minio(
                    endpoint=minio_endpoint,
                    access_key=minio_access_key,
                    secret_key=minio_secret_key,
                    secure=secure
                )
                logging.info(f"MinIO client initialized: {minio_endpoint} (secure={secure})")
            except Exception as e:
                logging.error(f"Failed to initialize MinIO client: {e}")
                raise
        return MinioClientSingleton._client






class ImageStorage:
    def __init__(self, storage_backend="hard", minio_client=None, base_upload_dir=None, bucket_prefix="default"):
        self.storage_backend = storage_backend
        self.minio_client = minio_client
        self.base_upload_dir = Path(base_upload_dir) if base_upload_dir else Path("/default/path")
        self.bucket_prefix = bucket_prefix

        image_types_env = settings.IMAGE_TYPES
        self.image_types = [image_type.strip() for image_type in image_types_env.split(",")]

        # Dynamically construct image_dirs based on image types
        self.image_dirs = {
            image_type: self.base_upload_dir / f"{image_type}" for image_type in self.image_types
        }

        if self.storage_backend == "hard":
            for dir_path in self.image_dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)

    def generate_unique_image_name(self, image_type):
        """Generate a unique image name using UUID."""
        unique_name = f"image_{image_type}_{uuid.uuid4().hex}.jpg"
        return unique_name

    async def save_image(self, image_type, image_input, camera_id=None, timestamp=None):

        if image_type not in self.image_dirs:
            raise ValueError(f"Invalid image type: {image_type}. Allowed types: {list(self.image_dirs.keys())}")

        # Determine directory path
        if image_type in ["plate_images", "traffic_images"]:  # High-volume types
            if not timestamp:
                raise ValueError("Timestamp is required for plate and car images.")
            year = timestamp.year
            month = f"{timestamp.month:02d}"
            day = f"{timestamp.day:02d}"
            hour = f"{timestamp.hour:02d}"

            db_path = Path(image_type) / str(camera_id) / str(year) / month / day / hour
            dir_path = self.base_upload_dir / db_path
            dir_path.mkdir(parents=True, exist_ok=True)
            bucket_name = f"{self.bucket_prefix}-{image_type}-{camera_id}-{year}-{month}-{day}-{hour}"
        else:  # Low-volume types
            dir_path = self.image_dirs[image_type]  # Changed line
            dir_path.mkdir(parents=True, exist_ok=True)
            bucket_name = f"{self.bucket_prefix}-{image_type}"
            db_path = Path(image_type)
            # db_path = Path(image_type)
            # dir_path = self.base_upload_dir / db_path
            # dir_path.mkdir(parents=True, exist_ok=True)
            # bucket_name = f"{self.bucket_prefix}-{image_type}"
            # if camera_id:
            #     bucket_name = f"{self.bucket_prefix}-{image_type}-{camera_id}"

        # Generate unique image name
        image_name = self.generate_unique_image_name(image_type)

        if isinstance(image_input, list):
            image_input = bytes(image_input)

        if isinstance(image_input, (UploadFile, StarletteUploadFile)):
            byte_array = await image_input.read()
        elif isinstance(image_input, (bytes, bytearray)):
            byte_array = image_input
        elif isinstance(image_input, str) or isinstance(image_input, Path):
            async with aiofiles.open(image_input, mode="rb") as f:
                byte_array = await f.read()
        else:
            raise ValueError("Unsupported image input type. Must be UploadFile, bytearray, or file path.")

        # Save the image based on the storage backend
        if self.storage_backend == "hard":
            file_path = dir_path / image_name
            await self._save_image_opencv(byte_array, file_path)
            return str(settings.BASE_UPLOAD_DIR/db_path / image_name)
        elif self.storage_backend == "minio":
            minio_path = self._sanitize_minio_path(db_path / image_name)
            await self._save_image_minio(byte_array, bucket_name, minio_path)
            return minio_path
        else:
            raise ValueError("Unsupported storage backend")

    def _sanitize_minio_path(self, path):

        sanitized_path = str(path).replace("\\", "/")  # Standardize separators
        # Add additional sanitization logic if needed
        return sanitized_path

    def list_objects_in_bucket(self, bucket_name, prefix=None):
        """
        List all object names in a given bucket.

        :param bucket_name: Name of the bucket to list objects from.
        :param prefix: Optional prefix to filter object names.
        :return: List of object names.
        """
        try:
            objects = self.minio_client.list_objects(bucket_name, prefix=prefix, recursive=True)
            object_names = [obj.object_name for obj in objects]
            print(object_names)
            return object_names
        except S3Error as e:
            print(f"Error: {e}")
            return []

    async def _save_image_opencv(self, byte_array, file_path):
        try:
            nparr = np.frombuffer(byte_array, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            async with aiofiles.open(file_path, mode='wb') as f:
                await f.write(cv2.imencode('.jpg', image)[1].tobytes())
            logger.info(f"Image saved successfully to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save image: {e}")

    async def _save_image_minio(self, byte_array, bucket_name, minio_path):
        bucket_name = bucket_name.replace("_", "-")

        try:
            # Check if bucket exists and create it if necessary
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully.")

            byte_stream = io.BytesIO(byte_array)

            self.minio_client.put_object(
                bucket_name=bucket_name,
                object_name=minio_path,
                data=byte_stream,
                length=len(byte_array),
                content_type="image/jpeg"
            )


            logger.info(f"Image saved successfully to MinIO at {minio_path} in bucket '{bucket_name}'")

        except Exception as e:
            logger.error(f"Failed to save image to MinIO: {e}")
            try:
                # Cleanup only if bucket exists
                if self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.remove_bucket(bucket_name)
                    logger.warning(f"Bucket '{bucket_name}' removed after failure.")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up bucket '{bucket_name}': {cleanup_error}")

    def object_exists(self, bucket_name, object_name):
        try:
            self.minio_client.stat_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            else:
                raise

    async def get_full_path(self, dir_path, expire_time=3600):
        """
        Returns the full path or MinIO download link based on the storage backend.
        :param dir_path: The saved directory path.
        :param image_name: The name of the image file.
        :param expire_time: Expiration time for the MinIO link in seconds (default: 3600 seconds).
        :return: Full local path or MinIO download link.
        """
        if self.storage_backend == "hard":
            return dir_path
        elif self.storage_backend == "minio":
            try:
                # Parse bucket name and object name from dir_path
                bucket_name, object_name = self._parse_minio_path(dir_path)

                if not isinstance(expire_time, int):
                    raise ValueError("expire_time must be an integer.")

                minio_path = self.minio_client.presigned_get_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=datetime.timedelta(seconds=3600)
                )

                # Return the URL
                return minio_path

            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {e}")
                raise
        else:
            raise ValueError("Unsupported storage backend")

    def _parse_minio_path(self, file_path):
        try:
            main_path = os.path.dirname(file_path)
            bucket_name = main_path.replace("/", "-").replace("\\", "-")
            bucket_name = bucket_name.replace("_", "-")
            bucket_name = f"{self.bucket_prefix}-{bucket_name}"
            file_path = self._sanitize_minio_path(file_path)
            return bucket_name, file_path
        except ValueError:
            raise ValueError(f"Invalid MinIO path format: {file_path}")

    async def delete_image(self, image_path: str) -> None:
        """
        Delete an image from the storage backend.

        Args:
            image_path (str): The path to the image (local path or MinIO object path).

        Raises:
            ValueError: If the storage backend is invalid.
            Exception: If the deletion fails.
        """
        try:
            if self.storage_backend == "hard":
                # Local storage deletion
                file_path = Path(image_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted local image: {file_path}")
                else:
                    logger.warning(f"Local image not found: {file_path}")

            elif self.storage_backend == "minio":
                # MinIO storage deletion
                bucket_name, object_name = self._parse_minio_path(image_path)

                if self.object_exists(bucket_name, object_name):
                    self.minio_client.remove_object(bucket_name, object_name)
                    logger.info(f"Deleted MinIO object: {object_name} from bucket {bucket_name}")
                else:
                    logger.warning(f"MinIO object not found: {object_name} in bucket {bucket_name}")

            else:
                raise ValueError(f"Unsupported storage backend: {self.storage_backend}")

        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            raise Exception(f"Failed to delete image: {e}")




class StorageFactory:
    _instance = None

    @staticmethod
    def get_instance(storage_backend="hard", base_upload_dir=None, bucket_prefix="default"):


        if StorageFactory._instance is None:

            if base_upload_dir is None:
                CURRENT_DIR = Path(__file__).resolve().parent
                PROJECT_ROOT = CURRENT_DIR.parent
                relative_upload_dir = settings.BASE_UPLOAD_DIR

                base_upload_dir = PROJECT_ROOT / relative_upload_dir

            StorageFactory._instance = StorageFactory.create_storage(
                storage_backend=storage_backend,
                base_upload_dir=base_upload_dir
            )
            print(f"ImageStorage initialized with backend: {storage_backend}")
        return StorageFactory._instance

    @staticmethod
    def create_storage(storage_backend="hard", base_upload_dir=None):
        if storage_backend == "hard":
            CURRENT_DIR = Path(__file__).resolve().parent
            PROJECT_ROOT = CURRENT_DIR.parent
            relative_upload_dir = settings.BASE_UPLOAD_DIR

            BASE_UPLOAD_DIR = PROJECT_ROOT / relative_upload_dir
            return ImageStorage(storage_backend="hard", base_upload_dir=BASE_UPLOAD_DIR)
        elif storage_backend == "minio":
            minio_client = MinioClientSingleton.get_instance()
            return ImageStorage(storage_backend="minio", minio_client=minio_client)
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
