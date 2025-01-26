import openpyxl
import shutil
from zipfile import ZipFile
from io import BytesIO
from fastapi import APIRouter, Depends, status, HTTPException, Query, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from settings import settings
from database.engine import get_db
from schema.traffic import TrafficCreate, TrafficInDB, TrafficPagination
from crud.traffic import TrafficOperation
from schema.user import UserInDB
from auth.authorization import get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only
from utils.middlewares import check_password_changed


BASE_UPLOAD_DIR = Path("uploads")
ZIP_FILE_DIR = BASE_UPLOAD_DIR / "zips"
ZIP_FILE_DIR.mkdir(parents=True, exist_ok=True)

dict_char_alpha = {
    'a':'ا', 'b': "ب", 'c': 'ص', 'd':'د', 'e': 'ژ', 'f':'ف', 'g':'گ', 'h':'ه', 'i':'ع','j': 'ج',
    'k':'ک', 'l':'ل', 'm':'م','n':'ن','o':'ث','q':'ق', 's':'س', 't':'ت','v':'و' , 'w':'ط', 'y':'ی',
    'p':'پ', 'u':'ش' , 'z':'ز', 'D':'D', 'S':'S',
}

# Create an APIRouter for user-related routes
traffic_router = APIRouter(
    prefix="/v1/traffic",
    tags=["traffic"],
)


@traffic_router.post("/", response_model=TrafficInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_traffic(
    traffic: TrafficCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    """
    Create a new vehicle.
    """
    traffic_op = TrafficOperation(db)
    return await traffic_op.create_traffic(traffic)


# Define a function to delete the file after sending it
def delete_file(path: Path):
    try:
        if path.exists():
            path.unlink()
            print(f"[INFO] Deleted file: {path}")
    except Exception as e:
        print(f"[ERROR] Failed to delete file: {path}. Error: {e}")


@traffic_router.get("/{traffic_id}", response_model=TrafficInDB, status_code=status.HTTP_200_OK)
async def get_one_traffic_data(
    request: Request,
    traffic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user),
):
    """
    Retrieve one traffic data.
    """
    # Extract the base URL and normalize it to include port 8000
    proto = request.headers.get("X-Forwarded-Proto", "http")
    raw_base_url = str(request.base_url).rstrip("/")
    base_url_without_port = raw_base_url.split("//")[1].split(":")[0]
    nginx_base_url = f"{proto}://{base_url_without_port}:8000"

    traffic_op = TrafficOperation(db)
    traffic = await traffic_op.get_one_object_id(traffic_id)

    # Modify plate image URLs for display in the response
    traffic.plate_image_url = None
    if traffic.plate_image:
        traffic.plate_image_url = f"{nginx_base_url}{traffic.plate_image}"
    traffic.full_image_url = None
    if traffic.full_image:
        traffic.full_image_url = f"{nginx_base_url}{traffic.full_image}"

    return traffic


@traffic_router.get("/", status_code=status.HTTP_200_OK)
async def get_traffic_data(
    request: Request,
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(10, ge=1, le=100, description="Number of records per page"),
    gate_id: int = Query(None, description="Filter by gate ID"),
    camera_id: int = Query(None, description="Filter by camera ID"),
    prefix_2: str = Query(None, description="First two digits of plate number"),
    alpha: str = Query(None, description="Alphabet character in plate number"),
    mid_3: str = Query(None, description="Three middle digits in plate number"),
    suffix_2: str = Query(None, description="Last two digits in plate number"),
    start_date: datetime = Query(None, description="Filter records from this date (ISO format)"),
    end_date: datetime = Query(None, description="Filter records up to this date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user),
):
    """
    Retrieve traffic data with pagination.
    """
    if end_date is not None and start_date is not None and end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be greater than start date."
        )

    proto = request.headers.get("X-Forwarded-Proto", "http")

    # Extract the base URL and normalize it to include port 8000
    raw_base_url = str(request.base_url).rstrip("/")
    base_url_without_port = raw_base_url.split("//")[1].split(":")[0]
    nginx_base_url = f"{proto}://{base_url_without_port}:8000/"

    traffic_op = TrafficOperation(db)
    paginated_result = await traffic_op.get_all_traffics(
        page=page,
        page_size=page_size,
        gate_id=gate_id,
        camera_id=camera_id,
        prefix_2=prefix_2,
        alpha=alpha,
        mid_3=mid_3,
        suffix_2=suffix_2,
        start_date=start_date,
        end_date=end_date
    )

    if not paginated_result["items"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No traffic data found for the given filters.")

    # Modify plate image URLs for display in the response
    for traffic in paginated_result["items"]:
        traffic.plate_image_url = None
        if traffic.plate_image:
            traffic.plate_image_url = f"{nginx_base_url}{traffic.plate_image}"
        traffic.full_image_url = None
        if traffic.full_image:
            traffic.full_image_url = f"{nginx_base_url}{traffic.full_image}"

    # Generate export link
    export_link = (
        f"{nginx_base_url}/v1/traffic/export?"
        f"gate_id={gate_id or ''}&"
        f"camera_id={camera_id or ''}&"
        f"prefix_2={prefix_2 or ''}&"
        f"alpha={alpha or ''}&"
        f"mid_3={mid_3 or ''}&"
        f"suffix_2={suffix_2 or ''}&"
        # f"plate_number={plate_number or ''}&"
        f"start_date={start_date.isoformat() if start_date else ''}&"
        f"end_date={end_date.isoformat() if end_date else ''}"
    )

    # Include export link in the response
    paginated_result["export_url"] = export_link

    return paginated_result


@traffic_router.get("/export", status_code=status.HTTP_200_OK)
async def export_traffic_data(
    request: Request,
    gate_id: int = Query(None, description="Filter by gate ID"),
    camera_id: int = Query(None, description="Filter by camera ID"),
    prefix_2: str = Query(None, description="First two digits of plate number"),
    alpha: str = Query(None, description="Alphabet character in plate number"),
    mid_3: str = Query(None, description="Three middle digits in plate number"),
    suffix_2: str = Query(None, description="Last two digits in plate number"),
    # plate_number: str = Query(None, description="Filter by partial or exact plate number"),
    start_date: datetime = Query(None, description="Filter records from this date (ISO format)"),
    end_date: datetime = Query(None, description="Filter records up to this date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_or_staff_user),
):
    """
    Generate a ZIP file containing traffic data and plate images (limited to 1000 records).
    """
    proto = request.headers.get("X-Forwarded-Proto", "http")
    base_url = str(request.base_url).split(":")[1].strip()  # Remove trailing slash if present
    nginx_base_url = f"{proto}:{base_url}" # Remove trailing slash if present

    traffic_op = TrafficOperation(db)

    # Get all matching data (limited to 1000 records)
    all_data_result = await traffic_op.get_all_traffics(
        page=1,
        page_size=1000,
        gate_id=gate_id,
        camera_id=camera_id,
        prefix_2=prefix_2,
        alpha=alpha,
        mid_3=mid_3,
        suffix_2=suffix_2,
        start_date=start_date,
        end_date=end_date
    )
    all_items = all_data_result["items"]

    if not all_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No traffic data found for the given filters.")

    # Temporary directory for file creation
    with TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Generate Excel file
        excel_path = temp_dir_path / "traffic_data.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Traffic Data"

        # Write headers
        headers = ["ID", "Plate Number", "OCR Accuracy", "Vision Speed", "Timestamp", "Camera ID", "Gate ID", "Plate Image"]
        ws.append(headers)

        def replace_with_persian_characters(plate_number: str, char_map: dict) -> str:
            return ''.join(char_map.get(char, char) for char in plate_number)


        # Write data rows
        for item in all_items:
            persian_plate_number = replace_with_persian_characters(item.plate_number, dict_char_alpha)
            item.plate_image_url = None
            if item.plate_image_path:
                filename = Path(item.plate_image_path).name
                item.plate_image_url = f"plate_images/{filename}"

            ws.append([
                item.id,
                persian_plate_number,
                # item.plate_number,
                item.ocr_accuracy,
                item.vision_speed,
                item.timestamp.isoformat(),
                item.camera_id,
                item.gate_id,
                item.plate_image_url,
            ])

        wb.save(excel_path)

        # Copy plate images to folder
        plate_images_dir = temp_dir_path / "plate_images"
        plate_images_dir.mkdir(parents=True, exist_ok=True)
        for item in all_items:
            if item.plate_image_path:
                source_image_path = Path(item.plate_image_path)
                if source_image_path.exists():
                    shutil.copyfile(source_image_path, plate_images_dir / source_image_path.name)

        # Create ZIP file
        zip_file_name = "traffic_data.zip"
        persistent_zip_path = Path("/tmp") / zip_file_name
        with ZipFile(persistent_zip_path, "w") as zip_file:
            zip_file.write(excel_path, arcname="traffic_data.xlsx")
            for image_file in plate_images_dir.iterdir():
                zip_file.write(image_file, arcname=f"plate_images/{image_file.name}")
        # Copy the ZIP file to the permanent directory
        permanent_zip_path = ZIP_FILE_DIR / zip_file_name
        shutil.copyfile(persistent_zip_path, permanent_zip_path)

    # Generate the download URL
    zip_file_url = f"{nginx_base_url}{permanent_zip_path}"

    return {"message": "Traffic data exported successfully.", "zip_file_url": zip_file_url}
