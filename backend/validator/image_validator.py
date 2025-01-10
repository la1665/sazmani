from fastapi import UploadFile, HTTPException, status
from typing import Optional

# Define allowed image MIME types and extensions
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png"]
ALLOWED_EXTENSIONS = ["jpeg", "jpg", "png"]

# Define maximum file size (in bytes)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image_extension(filename: Optional[str]=None):
    """
    Validates the file extension of the uploaded image.

    :param filename: Name of the uploaded file
    :raises HTTPException: If the file extension is not allowed
    """
    if filename:
        extension = filename.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '.{extension}'. Allowed extensions: {ALLOWED_EXTENSIONS}",
            )


def validate_image_content_type(content_type: Optional[str]=None):
    """
    Validates the MIME type of the uploaded image.

    :param content_type: MIME type of the uploaded file
    :raises HTTPException: If the MIME type is not allowed
    """
    if content_type:
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type '{content_type}'. Allowed types: {ALLOWED_MIME_TYPES}",
            )


def validate_image_size(file: UploadFile):
    """
    Validates the size of the uploaded image.

    :param file: UploadFile object
    :raises HTTPException: If the file size exceeds the maximum limit
    """
    file.file.seek(0, 2)  # Move the cursor to the end of the file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset the cursor to the beginning of the file
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )
