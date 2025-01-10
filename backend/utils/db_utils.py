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
from schema.user import UserCreate
from schema.building import BuildingCreate
from schema.gate import GateCreate
from schema.camera_setting import CameraSettingCreate
from schema.lpr_setting import LprSettingCreate
from schema.lpr import LprCreate
from schema.camera import CameraCreate
from tcp.tcp_manager import add_connection


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
    "gate_type": GateType.BOTH.name,
    "building_id": 1,
    "is_active": True,
    "created_at": datetime.utcnow(),  # Add timestamp
    "updated_at": datetime.utcnow(),
}

default_camera_settings = [
    {"name": "ViewPointX", "value": "0", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ViewPointY", "value": "0", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ViewPointWidth", "value": "1920", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ViewPointHeight", "value": "1080", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "MaxDeviation", "value": "100", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "MinDeviation", "value": "5", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ObjectSize", "value": "250", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "BufferSize", "value": "10", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "CameraDelayTime", "value": "200", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "CameraAddress", "value": "D:\\programs\\test_video\\s2.avi", "setting_type":SettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "live_scale", "value": "1", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "recive_plate_status", "value": "0", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "relay_ip", "value": "192.168.1.91", "setting_type":SettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "relay_port", "value": "2000", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "type_of_link", "value": "video", "setting_type":SettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "num_frame_process", "value": "1", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "num_send_frame", "value": "1", "setting_type":SettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
]


default_lpr_settings = [
    {"name": "deep_plate_width_1", "value": "640", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "heartbeat_interval", "value": "20", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_plate_width_2", "value": "640", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_plate_height", "value": "480", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_width", "value": "1280", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_height", "value": "736", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_detect_prob", "value": "0.55", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "max_IOU", "value": "0.95", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "min_IOU", "value": "0.85", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "nation_alpr", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ocr_file", "value": "ocr_int_model_1.xml", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "plate_detection_file", "value": "plate_model.xml", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "car_file", "value": "car_model.xml", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ocr_prob", "value": "0.65", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "plate_width", "value": "30", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "plate_height", "value": "10", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "live_scale", "value": "1", "setting_type": LprSettingType.INT,"is_active": True,  "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "recive_plate_status", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "relay_ip", "value": "192.168.1.91", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "relay_port", "value": "2000", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "video", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "debug", "value": "1", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "show_live", "value": "1", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "use_cpu", "value": "1", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "last_read_send", "value": "1", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "use_cuda", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "TCP_IP", "value": "3", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "car_detection", "value": "1", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "car_detection_scale", "value": "0.2", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "multi_language", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_car_width", "value": "512", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "deep_car_height", "value": "256", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "start_car_detect", "value": "0.6", "setting_type": LprSettingType.FLOAT,"is_active": True,  "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "base_path", "value": "D:\\home\\linaro\\images", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "db_adress", "value": "D:\\client_firefox\\transist.db", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "mysql_user", "value": "root", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "mysql_pass", "value": "1234", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "database", "value": "parking2", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "mysql_host", "value": "localhost", "setting_type": LprSettingType.STRING, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "track_plates", "value": "0", "setting_type": LprSettingType.INT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),},
    {"name": "ocr_prob", "value": "0.65", "setting_type": LprSettingType.FLOAT, "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),}
]

default_lpr = {
    "name": "ماژول ۱",
    "description": "پلاک خوان دوربین گیت۱ برای ورودی/خروجی",
    # "ip": "185.81.99.23",
    "ip": "192.168.65.254",
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
        print("connecting to twisted ...")
        await add_connection(db, lpr_id=db_camera.lpr_id)
    else:
        camera_obj = CameraCreate(
        name=default_camera["name"],
        description=default_camera["description"],
        latitude=default_camera["latitude"],
        longitude=default_camera["longitude"],
        gate_id=default_camera["gate_id"],
        lpr_id=db_lpr.id,
        )
        new_camera = await camera_op.create_camera(camera_obj)
        print(f"Created camera with ID: {new_camera.id}")
        await add_connection(db, lpr_id=new_camera.lpr_id)
    print("default cameras created!!!")
