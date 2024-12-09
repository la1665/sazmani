# from minio import Minio
# from minio.error import S3Error

# from settings import settings


# # Initialize MinIO client
# minio_client = Minio(
#     settings.MINIO_ENDPOINT,
#     access_key=settings.MINIO_ACCESS_KEY,
#     secret_key=settings.MINIO_SECRET_KEY,
#     secure=settings.MINIO_USE_SSL
# )

# # Ensure the bucket exists

# try:
#     if not minio_client.bucket_exists(settings.MINIO_PROFILE_IMAGE_BUCKET):
#         minio_client.make_bucket(settings.MINIO_PROFILE_IMAGE_BUCKET)
#         print(f"Bucket '{settings.MINIO_PROFILE_IMAGE_BUCKET}' created.")
#     else:
#         print(f"Bucket '{settings.MINIO_PROFILE_IMAGE_BUCKET}' already exists.")
#     # Full image bucket for vehicle images
#     if not minio_client.bucket_exists(settings.MINIO_FULL_IMAGE_BUCKET):
#         minio_client.make_bucket(settings.MINIO_FULL_IMAGE_BUCKET)
#         print(f"Bucket '{settings.MINIO_FULL_IMAGE_BUCKET}' created.")
#     else:
#         print(f"Bucket '{settings.MINIO_FULL_IMAGE_BUCKET}' already exists.")

#     # Plate image bucket for vehicle plate images
#     if not minio_client.bucket_exists(settings.MINIO_PLATE_IMAGE_BUCKET):
#         minio_client.make_bucket(settings.MINIO_PLATE_IMAGE_BUCKET)
#         print(f"Bucket '{settings.MINIO_PLATE_IMAGE_BUCKET}' created.")
#     else:
#         print(f"Bucket '{settings.MINIO_PLATE_IMAGE_BUCKET}' already exists.")

# except S3Error as error:
#     print(f"Error creating buckets '{error}'")
