from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models.user import UserType
from models.gate import GateType
from models.camera_setting import SettingType
from models.lpr_setting import LprSettingType
from settings import settings
from crud.user import UserOperation
from crud.building import BuildingOperation
from crud.gate import GateOperation
from crud.camera_setting import CameraSettingOperation
from crud.lpr_setting import LprSettingOperation
from crud.lpr import LprOperation
from crud.camera import CameraOperation
from crud.status import StatusOperation
from schema.user import UserCreate
from schema.building import BuildingCreate
from schema.gate import GateCreate
from schema.camera_setting import CameraSettingCreate
from schema.lpr_setting import LprSettingCreate
from schema.lpr import LprCreate
from schema.camera import CameraCreate
from schema.status import StatusCreate
# from tcp.tcp_manager import add_connection


default_building = {
    "name": "مرکزی",
    "latitude": "98.0.0",
    "longitude": "98.0.0",
    "description": "شعبه مرکزی",
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),  # Add timestamp
}

default_gate = {
    "name": "گیت اصلی ساختمان مرکزی",
    "description": "گیت اصلی شعبه مرکزی تهران",
    "gate_type": GateType.BOTH,
    "building_id": 1,
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
}

default_camera_settings = [
    {
        "name": "ViewPointX",
        "value": "0",
        "description": "The X-coordinate of the camera's viewpoint in the scene.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ViewPointY",
        "value": "0",
        "description": "The Y-coordinate of the camera's viewpoint in the scene.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ViewPointWidth",
        "value": "1920",
        "description": "The width of the camera's field of view in pixels.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ViewPointHeight",
        "value": "1080",
        "description": "The height of the camera's field of view in pixels.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "MaxDeviation",
        "value": "100",
        "description": "The maximum allowable deviation in object detection.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "MinDeviation",
        "value": "5",
        "description": "The minimum deviation threshold to detect an object.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ObjectSize",
        "value": "250",
        "description": "The expected size of the object to be detected in pixels.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "BufferSize",
        "value": "10",
        "description": "The number of frames to buffer for processing.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "CameraDelayTime",
        "value": "200",
        "description": "The delay time in milliseconds before capturing the next frame.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "CameraAddress",
        "value": "D:\\programs\\test_video\\s2.avi",
        "description": "The file path or network address of the camera feed.",
        "setting_type": SettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "live_scale",
        "value": "1",
        "description": "Scale factor for live video feed display.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "recive_plate_status",
        "value": "0",
        "description": "Status flag indicating if plate data has been received (0 for no, 1 for yes).",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "relay_ip",
        "value": "192.168.1.91",
        "description": "The IP address of the relay device connected to the camera.",
        "setting_type": SettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "relay_port",
        "value": "2000",
        "description": "The network port number used for relay communication.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "type_of_link",
        "value": "video",
        "description": "The type of connection to the camera (e.g., 'video' or 'stream').",
        "setting_type": SettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "num_frame_process",
        "value": "1",
        "description": "The number of frames to process in each batch.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "num_send_frame",
        "value": "1",
        "description": "The number of frames to send per transmission.",
        "setting_type": SettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
]

default_lpr_settings = [
    {
        "name": "deep_plate_width_1",
        "value": "640",
        "description": "Width of the first detection region for license plates in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "heartbeat_interval",
        "value": "20",
        "description": "Interval in seconds for sending heartbeat signals to ensure system health.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_plate_width_2",
        "value": "640",
        "description": "Width of the second detection region for license plates in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_plate_height",
        "value": "480",
        "description": "Height of the detection region for license plates in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_width",
        "value": "1280",
        "description": "Width of the deep learning model's input frame in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_height",
        "value": "736",
        "description": "Height of the deep learning model's input frame in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_detect_prob",
        "value": "0.55",
        "description": "Minimum probability threshold for detecting license plates using deep learning.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "max_IOU",
        "value": "0.95",
        "description": "Maximum Intersection Over Union (IOU) for bounding box overlap in detection.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "min_IOU",
        "value": "0.85",
        "description": "Minimum Intersection Over Union (IOU) threshold for valid detections.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "nation_alpr",
        "value": "0",
        "description": "Flag indicating if national license plate recognition rules are applied (0 for no, 1 for yes).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ocr_file",
        "value": "ocr_int_model_1.xml",
        "description": "File path for the Optical Character Recognition (OCR) model used in plate detection.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "plate_detection_file",
        "value": "plate_model.xml",
        "description": "File path for the model used to detect license plates.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "car_file",
        "value": "car_model.xml",
        "description": "File path for the model used to detect vehicles.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "ocr_prob",
        "value": "0.65",
        "description": "Minimum confidence threshold for OCR results on detected plates.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "plate_width",
        "value": "30",
        "description": "Expected width of detected license plates in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "plate_height",
        "value": "10",
        "description": "Expected height of detected license plates in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "live_scale",
        "value": "1",
        "description": "Scale factor for displaying live video feed.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "recive_plate_status",
        "value": "0",
        "description": "Status flag indicating whether plate data has been received (0 for no, 1 for yes).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "relay_ip",
        "value": "192.168.1.91",
        "description": "IP address of the relay device used for external communication.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "relay_port",
        "value": "2000",
        "description": "Network port number for relay communication.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "video",
        "value": "0",
        "description": "Flag to enable or disable video feed (0 for disabled, 1 for enabled).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "debug",
        "value": "1",
        "description": "Enables debug mode for logging detailed system information.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "show_live",
        "value": "1",
        "description": "Displays live camera feed on the interface (1 to enable, 0 to disable).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "use_cpu",
        "value": "1",
        "description": "Flag to enforce processing on CPU instead of GPU (1 for CPU, 0 for GPU).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "use_cuda",
        "value": "0",
        "description": "Enables CUDA acceleration if set to 1, otherwise uses CPU.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "car_detection",
        "value": "1",
        "description": "Flag to enable car detection in the video feed (1 to enable, 0 to disable).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "car_detection_scale",
        "value": "0.2",
        "description": "Scale factor applied when detecting cars in the frame.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "multi_language",
        "value": "0",
        "description": "Flag to enable support for multiple languages in OCR (1 for enabled, 0 for disabled).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_car_width",
        "value": "512",
        "description": "Width of the car detection input for deep learning models in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "deep_car_height",
        "value": "256",
        "description": "Height of the car detection input for deep learning models in pixels.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "start_car_detect",
        "value": "0.6",
        "description": "Confidence threshold for starting car detection.",
        "setting_type": LprSettingType.FLOAT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "base_path",
        "value": "D:\\home\\linaro\\images",
        "description": "Base directory path where images and video data are stored.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "db_adress",
        "value": "D:\\client_firefox\\transist.db",
        "description": "File path for the SQLite database used by the system.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "mysql_user",
        "value": "root",
        "description": "Username for connecting to the MySQL database.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "mysql_pass",
        "value": "1234",
        "description": "Password for the MySQL database connection.",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "database",
        "value": "parking2",
        "description": "Name of the MySQL database used for storing license plate recognition data.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "mysql_host",
        "value": "localhost",
        "description": "Host address of the MySQL server.",
        "setting_type": LprSettingType.STRING,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    },
    {
        "name": "track_plates",
        "value": "0",
        "description": "Flag to enable tracking of detected license plates (1 for enabled, 0 for disabled).",
        "setting_type": LprSettingType.INT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
]

default_lpr = {
    "name": "ماژول ۱",
    "description": "پلاک خوان دوربین گیت۱ برای ورودی/خروجی",
    "ip": "185.81.99.23",
    # "ip": "192.168.65.254",
    "port": 45,
    "auth_token": "dBzsEzYuBy6wgiGlI4UUXJPLp1OoS0Cc2YgyCFOCh2U7pvH16ucL1334OjCmeWFJ",
    "latitude": "98.0.0",
    "longitude": "98.0.0",
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
}

default_camera = {
    "name": "دوربین اصلی",
    "latitude": "1.0.1",
    "longitude": "1.0.1",
    "description": "دوربین اصلی گیت",
    "gate_id": 1,
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
}

default_status = [
    {
    "name": "No_action",
    "description": "وضعیت پیش فرض",
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
    },
    {
    "name": "Valid",
    "description": "وضعیت مجاز",
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
    },
    {
    "name": "Invalid",
    "description": "وضعبت غیر مجاز",
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
    },
]

async def create_default_admin(db: AsyncSession):
    if settings.ADMIN_PERSONAL_NUMBER:
        user_op = UserOperation(db)
        db_admin = await user_op.get_user_personal_number(settings.ADMIN_PERSONAL_NUMBER)
        if db_admin:
            print("Admin user already exists.")
            return

        admin = UserCreate(
            personal_number=settings.ADMIN_PERSONAL_NUMBER,
            national_id=settings.ADMIN_NATIONAL_ID,
            first_name=settings.ADMIN_FIRST_NAME,
            last_name=settings.ADMIN_LAST_NAME,
            office=settings.ADMIN_OFFICE,
            phone_number=settings.ADMIN_PHONE_NUMBER,
            email=settings.ADMIN_EMAIL,
            user_type=UserType.ADMIN,
        )
        admin = await user_op.create_user(admin)
        print("Admin user created.")

async def initialize_defaults(db: AsyncSession):

    building_op = BuildingOperation(db)
    db_building = await building_op.get_one_object_name(default_building["name"])
    if db_building:
        print("building object already exists.")
    else:
        building_obj = BuildingCreate(
            name=default_building["name"],
            description=default_building["description"],
            latitude=default_building["latitude"],
            longitude=default_building["longitude"],
        )
        db_building = await building_op.create_building(building_obj)
        print(f"Created building with ID: {db_building.id}")
    print("default building created!!!")

    gate_op = GateOperation(db)
    db_gate = await gate_op.get_one_object_name(default_gate["name"])
    if db_gate:
        print("gate object already exists.")
    else:
        gate_obj = GateCreate(
            name=default_gate["name"],
            description=default_gate["description"],
            gate_type=default_gate["gate_type"],
            building_id=db_building.id,
        )
        db_gate = await gate_op.create_gate(gate_obj)
        print(f"Created gate with ID: {db_gate.id}")
    print("default gate created!!!")

    camera_setting_op = CameraSettingOperation(db)
    for setting in default_camera_settings:
        existing_setting = await camera_setting_op.get_one_object_name(setting.get("name"))
        if existing_setting is None:
            cam_setting_obj = CameraSettingCreate(
                name=setting["name"],
                description=setting.get("description", ""),
                value=setting["value"],
                setting_type=setting["setting_type"]
            )
            new_setting = await camera_setting_op.create_setting(cam_setting_obj)
            print(f"Created camera setting with ID: {new_setting.id}")
    print("default camera settings created!!!")

    lpr_setting_op = LprSettingOperation(db)
    for setting in default_lpr_settings:
        existing_setting = await lpr_setting_op.get_one_object_name(setting.get("name"))
        if existing_setting is None:
            lpr_setting_obj = LprSettingCreate(
                name=setting["name"],
                description=setting.get("description", ""),
                setting_type=setting["setting_type"],
                value=setting["value"],
            )
            new_setting = await lpr_setting_op.create_setting(lpr_setting_obj)
            print(f"Created lpr setting with ID: {new_setting.id}")
    print("default lpr settings created!!!")


    lpr_op = LprOperation(db)
    db_lpr = await lpr_op.get_one_object_name(default_lpr["name"])
    if db_lpr:
        print("lpr object already exists.")
    else:
        lpr_obj = LprCreate(
            name=default_lpr["name"],
            description=default_lpr["description"],
            latitude=default_lpr["latitude"],
            longitude=default_lpr["longitude"],
            ip=default_lpr["ip"],
            port=default_lpr["port"],
        )
        db_lpr = await lpr_op.create_lpr(lpr_obj)
        print(f"Created lpr with ID: {db_lpr.id}")
    print("default lprs created!!!")


    camera_op = CameraOperation(db)
    db_camera = await camera_op.get_one_object_name(default_camera.get("name"))
    if db_camera:
        print("camera object already exists.")
        # print("connecting to twisted ...")
        # await add_connection(db, lpr_id=db_camera.lpr_id)
    else:
        camera_obj = CameraCreate(
        name=default_camera["name"],
        description=default_camera["description"],
        latitude=default_camera["latitude"],
        longitude=default_camera["longitude"],
        gate_id=db_gate.id,
        lpr_id=db_lpr.id,
        )
        new_camera = await camera_op.create_camera(camera_obj)
        print(f"Created camera with ID: {new_camera.id}")
        # await add_connection(db, lpr_id=new_camera.lpr_id)
    print("default cameras created!!!")


    status_op = StatusOperation(db)
    for stat in default_status:
        db_status = await status_op.get_one_object_name(stat.get("name"))
        if db_status:
            print("Status object already exists.")
        else:
            status_obj = StatusCreate(
            name=stat["name"],
            description=stat["description"],
            )
            new_status = await status_op.create_status(status_obj)
            print(f"Created status with ID: {new_status.id}")
    print("default status created!!!")
