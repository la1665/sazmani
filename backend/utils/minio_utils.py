# import io
# import base64
# from fastapi import HTTPException, status
# from minio import S3Error
# from datetime import datetime, date

# from database.minio_engine import minio_client
# from settings import settings


# def upload_profile_image(file_data: bytes, user_id: int, username: str, original_filename: str, content_type: str) -> str:
#     """
#     Uploads a profile image to MinIO and returns the URL.
#     The filename will be formatted as '{user_id}-{original_filename}'.
#     """
#     unique_filename = generate_unique_filename(user_id, username, original_filename)
#     file_length = len(file_data)
#     try:
#         # Upload file to MinIO
#         minio_client.put_object(
#             bucket_name=settings.MINIO_PROFILE_IMAGE_BUCKET,
#             object_name=unique_filename,
#             data=io.BytesIO(file_data),
#             length=file_length,
#             content_type=content_type  # Adjust based on file type
#         )
#         return unique_filename

#     except S3Error as error:
#         print(f"Error uploading profile image: {error}")
#         raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Failed to upload profile image."
#             )


# def delete_profile_image(filename: str) -> None:
#     """
#     Deletes a profile image from MinIO.
#     """
#     try:
#         minio_client.remove_object(settings.MINIO_PROFILE_IMAGE_BUCKET, filename)
#         print(f"Deleted profile image: {filename}")
#     except S3Error as e:
#         print(f"Error deleting profile image: {e}")
#         raise



# def upload_vehicle_full_image(base64_image, filename: str, content_type: str) -> str:
#     """
#     Uploads a full vehicle image to the designated MinIO bucket and returns the URL.
#     """
#     image_data = base64.b64decode(base64_image)
#     image_bytes = io.BytesIO(image_data)

#     try:
#         # Upload full image to MinIO
#         minio_client.put_object(
#             bucket_name=settings.MINIO_FULL_IMAGE_BUCKET,
#             object_name=filename,
#             data=image_bytes,
#             length=len(image_data),
#             content_type=content_type
#         )

#         # Generate a pre-signed URL for accessing the image
#         image_url = minio_client.presigned_get_object(
#             settings.MINIO_FULL_IMAGE_BUCKET, filename
#         )
#         return image_url

#     except S3Error as error:
#         print(f"Error uploading full vehicle image: {error}")
#         raise

# def delete_vehicle_full_image(filename: str) -> None:
#     """
#     Deletes a full vehicle image from MinIO.
#     """
#     try:
#         minio_client.remove_object(settings.MINIO_FULL_IMAGE_BUCKET, filename)
#         print(f"Deleted full vehicle image: {filename}")
#     except S3Error as e:
#         print(f"Error deleting full vehicle image: {e}")
#         raise

# def upload_vehicle_plate_image(base64_image, filename: str, content_type: str) -> str:
#     """
#     Uploads a vehicle plate image to the designated MinIO bucket and returns the URL.
#     """
#     image_data = base64.b64decode(base64_image)
#     image_bytes = io.BytesIO(image_data)
#     try:
#         # Upload plate image to MinIO
#         minio_client.put_object(
#             bucket_name=settings.MINIO_PLATE_IMAGE_BUCKET,
#             object_name=filename,
#             data=image_bytes,
#             length=len(image_data),
#             content_type=content_type
#         )

#         # Generate a pre-signed URL for accessing the image
#         image_url = minio_client.presigned_get_object(
#             settings.MINIO_PLATE_IMAGE_BUCKET, filename
#         )
#         return image_url

#     except S3Error as error:
#         print(f"Error uploading vehicle plate image: {error}")
#         raise

# def delete_vehicle_plate_image(filename: str) -> None:
#     """
#     Deletes a vehicle plate image from MinIO.
#     """
#     try:
#         minio_client.remove_object(settings.MINIO_PLATE_IMAGE_BUCKET, filename)
#         print(f"Deleted vehicle plate image: {filename}")
#     except S3Error as e:
#         print(f"Error deleting vehicle plate image: {e}")
#         raise




# def generate_unique_filename(user_id: int, username: str, original_filename: str) -> str:
#     """
#     Generate a unique filename for a user's profile image.

#     Args:
#         user_id (int): The user's ID.
#         username (str): The user's username, or `None` if not provided.
#         original_filename (str): The original filename uploaded by the user.

#     Returns:
#         str: A sanitized and unique filename.
#     """
#     # Extract the file extension from the original filename
#     file_extension = original_filename.split('.')[-1].lower()

#     # Use 'null' if username is None
#     sanitized_username = username or "null"

#     # Create a unique filename with the date and sanitized values
#     current_date = date.today().strftime("%Y-%m-%d")
#     unique_filename = f"{user_id}-{sanitized_username}-{current_date}.{file_extension}"

#     return unique_filename
