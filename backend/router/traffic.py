import openpyxl
import shutil
from zipfile import ZipFile
from io import BytesIO
from fastapi import APIRouter, Depends, status, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from fastapi.responses import FileResponse
from pathlib import Path
from tempfile import TemporaryDirectory


from settings import settings
from database.engine import get_db
from schema.traffic import TrafficCreate, TrafficInDB, TrafficPagination
from crud.traffic import TrafficOperation
from schema.user import UserInDB
from auth.authorization import get_admin_user, get_admin_or_staff_user, get_self_or_admin_or_staff_user, get_self_or_admin_user, get_self_user_only
from utils.middlewwares import check_password_changed


# Create an APIRouter for user-related routes
traffic_router = APIRouter(
    prefix="/v1/traffic",
    tags=["traffic"],
)


@traffic_router.post("/", response_model=TrafficInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_traffic(
    traffic: TrafficCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB=Depends(get_admin_user)
):
    """
    Create a new vehicle.
    """
    traffic_op = TrafficOperation(db)
    return await traffic_op.create_traffic(traffic)


@traffic_router.get("/", response_model=TrafficPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_traffic(
    request: Request,
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(10, ge=1, le=100, description="Number of records per page"),
    gate_id: int = Query(None, description="Filter by gate ID"),
    camera_id: int = Query(None, description="Filter by camera ID"),
    plate_number: str = Query(None, description="Filter by partial or exact plate number"),
    start_date: datetime = Query(None, description="Filter records from this date (ISO format)"),
    end_date: datetime = Query(None, description="Filter records up to this date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user)
):
    """
    Retrieve all vehicles with pagination.
    """
    traffic_op = TrafficOperation(db)
    result = await traffic_op.get_all_traffics(
            page=page,
            page_size=page_size,
            gate_id=gate_id,
            camera_id=camera_id,
            plate_number=plate_number,
            start_date=start_date,
            end_date=end_date
        )
    for traffic in result["items"]:
        traffic.plate_image_url = None
        if traffic.plate_image_path:
            filename = Path(traffic.plate_image_path).name
            traffic.plate_image_url = f"{request.base_url}uploads/plate_images/{filename}"

    # Add export URL to the response
    export_url = f"/v1/traffic/export?page={page}&page_size={page_size}"
    if gate_id:
        export_url += f"&gate_id={gate_id}"
    if camera_id:
        export_url += f"&camera_id={camera_id}"
    if plate_number:
        export_url += f"&plate_number={plate_number}"
    if start_date:
        export_url += f"&start_date={start_date.isoformat()}"
    if end_date:
        export_url += f"&end_date={end_date.isoformat()}"

    return {
        **result,
        "export_url": export_url
    }


@traffic_router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    responses={200: {"content": {"application/zip": {}}}}
)
async def export_traffic_data(
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(10, ge=1, le=100, description="Number of records per page"),
    gate_id: int = Query(None, description="Filter by gate ID"),
    camera_id: int = Query(None, description="Filter by camera ID"),
    plate_number: str = Query(None, description="Filter by partial or exact plate number"),
    start_date: datetime = Query(None, description="Filter records from this date (ISO format)"),
    end_date: datetime = Query(None, description="Filter records up to this date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user)
):
    """
    Export traffic records to Excel with the same filters as the main API.
    """
    traffic_op = TrafficOperation(db)
    result = await traffic_op.get_all_traffics(
        page=page,
        page_size=page_size,
        gate_id=gate_id,
        camera_id=camera_id,
        plate_number=plate_number,
        start_date=start_date,
        end_date=end_date
    )

    # If no data, raise a 404
    if not result["items"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data found for the given filters.")

    # Create Excel file
    with TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create the Excel file
        excel_path = temp_dir_path / "traffic_data.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Traffic Data"

        # Write headers
        headers = ["ID", "Plate Number", "OCR Accuracy", "Vision Speed", "Timestamp", "Camera ID", "Gate ID"]
        ws.append(headers)

        # Write data rows
        for item in result["items"]:
            ws.append([
                item.id,
                item.plate_number,
                item.ocr_accuracy,
                item.vision_speed,
                item.timestamp.isoformat(),
                item.camera_id,
                item.gate_id,
            ])

        wb.save(excel_path)

        # Create the `plate_images` directory
        plate_images_dir = temp_dir_path / "plate_images"
        plate_images_dir.mkdir(parents=True, exist_ok=True)

        # Copy the images to the `plate_images` folder
        for item in result["items"]:
            if item.plate_image_path:
                source_image_path = Path(item.plate_image_path)
                if source_image_path.exists():
                    destination_image_path = plate_images_dir / source_image_path.name
                    shutil.copyfile(source_image_path, destination_image_path)

        # Create the zip file
        zip_file_path = temp_dir_path / "traffic_data.zip"
        with ZipFile(zip_file_path, "w") as zip_file:
            # Add the Excel file to the zip
            zip_file.write(excel_path, arcname="traffic_data.xlsx")

            # Add images to the zip
            for image_file in plate_images_dir.iterdir():
                zip_file.write(image_file, arcname=f"plate_images/{image_file.name}")

        # Move the zip file to a persistent location
        persistent_zip_path = Path(temp_dir).parent / "traffic_data.zip"
        shutil.move(zip_file_path, persistent_zip_path)

    # Return the zip file as a response
    return FileResponse(
        path=persistent_zip_path,
        media_type="application/zip",
        filename="traffic_data.zip"
    )
