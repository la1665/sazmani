from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserType
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


default_users = [
    {
        "username":"2",
        "email":"user2@example.com",
        "user_type":UserType.STAFF,
        "password":"2"
    },
    # {
    #     "username":"3",
    #     "email":"user3@example.com",
    #     "user_type":UserType.STAFF,
    #     "password":"3"
    # },
    # {
    #     "username":"4",
    #     "email":"user4@example.com",
    #     "user_type":UserType.VIEWER,
    #     "password":"4"
    # },
    # {
    #     "username":"5",
    #     "email":"user5@example.com",
    #     "user_type":UserType.USER,
    #     "password":"5"
    # },
    # {
    #     "username":"6",
    #     "email":"user6@example.com",
    #     "user_type":UserType.USER,
    #     "password":"6"
    # },
]


default_buildings = [
    {
      "name": "مرکزی",
      "latitude": "98.0.0",
      "longitude": "98.0.0",
      "description": "شعبه مرکزی"
    },
    {
      "name": "آمل",
      "latitude": "98.0.1",
      "longitude": "98.0.1",
      "description": "شعبه آمل"
    }
]

default_gates = [
    {
      "name": "گیت اصلی ساختمان مرکزی",
      "description": "گیت اصلی شعبه مرکزی تهران",
      "gate_type": 2,
      "building_id": 1
    },
    {
      "name": "گیت ورودی/خروجی شعبه",
      "description": "گیت اصلی شعبه آمل",
      "gate_type": 2,
      "building_id": 2
    }
]

default_camera_settings = [
    {"name": "ViewPointX", "value": "0", "setting_type":SettingType.INT},
    {"name": "ViewPointY", "value": "0", "setting_type":SettingType.INT},
    {"name": "ViewPointWidth", "value": "1920", "setting_type":SettingType.INT},
    {"name": "ViewPointHeight", "value": "1080", "setting_type":SettingType.INT},
    {"name": "MaxDeviation", "value": "100", "setting_type":SettingType.INT},
    {"name": "MinDeviation", "value": "5", "setting_type":SettingType.INT},
    {"name": "ObjectSize", "value": "250", "setting_type":SettingType.INT},
    {"name": "BufferSize", "value": "10", "setting_type":SettingType.INT},
    {"name": "CameraDelayTime", "value": "200", "setting_type":SettingType.INT},
    {"name": "CameraAddress", "value": "D:\\programs\\test_video\\s2.avi", "setting_type":SettingType.STRING},
    {"name": "live_scale", "value": "1", "setting_type":SettingType.INT},
    {"name": "recive_plate_status", "value": "0", "setting_type":SettingType.INT},
    {"name": "relay_ip", "value": "192.168.1.91", "setting_type":SettingType.STRING},
    {"name": "relay_port", "value": "2000", "setting_type":SettingType.INT},
    {"name": "type_of_link", "value": "video", "setting_type":SettingType.STRING},
    {"name": "num_frame_process", "value": "1", "setting_type":SettingType.INT},
    {"name": "num_send_frame", "value": "1", "setting_type":SettingType.INT},
]


default_lpr_settings = [
    {"name": "deep_plate_width_1", "value": "640", "setting_type": LprSettingType.INT},
    {"name": "heartbeat_interval", "value": "20", "setting_type": LprSettingType.INT},
    {"name": "deep_plate_width_2", "value": "640", "setting_type": LprSettingType.INT},
    {"name": "deep_plate_height", "value": "480", "setting_type": LprSettingType.INT},
    {"name": "deep_width", "value": "1280", "setting_type": LprSettingType.INT},
    {"name": "deep_height", "value": "736", "setting_type": LprSettingType.INT},
    {"name": "deep_detect_prob", "value": "0.55", "setting_type": LprSettingType.FLOAT},
    {"name": "max_IOU", "value": "0.95", "setting_type": LprSettingType.FLOAT},
    {"name": "min_IOU", "value": "0.85", "setting_type": LprSettingType.FLOAT},
    {"name": "nation_alpr", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "ocr_file", "value": "ocr_int_model_1.xml", "setting_type": LprSettingType.STRING},
    {"name": "plate_detection_file", "value": "plate_model.xml", "setting_type": LprSettingType.STRING},
    {"name": "car_file", "value": "car_model.xml", "setting_type": LprSettingType.STRING},
    {"name": "ocr_prob", "value": "0.65", "setting_type": LprSettingType.FLOAT},
    {"name": "plate_width", "value": "30", "setting_type": LprSettingType.INT},
    {"name": "plate_height", "value": "10", "setting_type": LprSettingType.INT},
    {"name": "live_scale", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "recive_plate_status", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "relay_ip", "value": "192.168.1.91", "setting_type": LprSettingType.STRING},
    {"name": "relay_port", "value": "2000", "setting_type": LprSettingType.INT},
    {"name": "video", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "debug", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "show_live", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "use_cpu", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "last_read_send", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "use_cuda", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "TCP_IP", "value": "3", "setting_type": LprSettingType.INT},
    {"name": "car_detection", "value": "1", "setting_type": LprSettingType.INT},
    {"name": "car_detection_scale", "value": "0.2", "setting_type": LprSettingType.FLOAT},
    {"name": "multi_language", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "deep_car_width", "value": "512", "setting_type": LprSettingType.INT},
    {"name": "deep_car_height", "value": "256", "setting_type": LprSettingType.INT},
    {"name": "start_car_detect", "value": "0.6", "setting_type": LprSettingType.FLOAT},
    {"name": "base_path", "value": "D:\\home\\linaro\\images", "setting_type": LprSettingType.STRING},
    {"name": "db_adress", "value": "D:\\client_firefox\\transist.db", "setting_type": LprSettingType.STRING},
    {"name": "mysql_user", "value": "root", "setting_type": LprSettingType.STRING},
    {"name": "mysql_pass", "value": "1234", "setting_type": LprSettingType.INT},
    {"name": "database", "value": "parking2", "setting_type": LprSettingType.STRING},
    {"name": "mysql_host", "value": "localhost", "setting_type": LprSettingType.STRING},
    {"name": "track_plates", "value": "0", "setting_type": LprSettingType.INT},
    {"name": "ocr_prob", "value": "0.65", "setting_type": LprSettingType.FLOAT}
]
# default_lpr_settings = [
#     {"name": "deep_plate_width_1", "description": "عرض تشخیص پلاک اول", "value": "640", "setting_type": LprSettingType.INT},
#     {"name": "deep_plate_width_2", "description": "عرض تشخیص پلاک دوم", "value": "640", "setting_type": LprSettingType.INT},
#     {"name": "deep_plate_height", "description": "ارتفاع تشخیص پلاک", "value": "480", "setting_type": LprSettingType.INT},
#     {"name": "deep_width", "description": "عرض تصویر تشخیص پلاک", "value": "1280", "setting_type": LprSettingType.INT},
#     {"name": "deep_height", "description": "ارتفاع تصویر تشخیص پلاک", "value": "736", "setting_type": LprSettingType.INT},
#     {"name": "deep_detect_prob", "description": "احتمال تشخیص پلاک", "value": "0.55", "setting_type": LprSettingType.FLOAT},
#     {"name": "max_IOU", "description": "بیشترین ترکیب تلاقی", "value": "0.95", "setting_type": LprSettingType.FLOAT},
#     {"name": "min_IOU", "description": "کمترین ترکیب تلاقی", "value": "0.85", "setting_type": LprSettingType.FLOAT},
#     {"name": "nation_alpr", "description": "تشخیص پلاک ملی", "value": "0", "setting_type": LprSettingType.INT},
#     {"name": "ocr_file", "description": "فایل OCR", "value": "ocr_int_model_1.xml", "setting_type": LprSettingType.STRING},
#     {"name": "plate_detection_file", "description": "فایل تشخیص پلاک", "value": "plate_model.xml", "setting_type": LprSettingType.STRING},
#     {"name": "car_file", "description": "فایل تشخیص خودرو", "value": "car_model.xml", "setting_type": LprSettingType.STRING},
#     {"name": "ocr_prob", "description": "احتمال انتخاب OCR", "value": "0.65", "setting_type": LprSettingType.FLOAT},
# ]

default_lprs = [
    {
      "name": "ماژول پلاک خوان۱",
      "description": "پلاک خوان دوربین گیت۱ برای ورودی/خروجی",
      "ip": "185.81.99.23",
      "port": 45,
      "latitude": "98.0.0",
      "longitude": "98.0.0",
    },
    # {
    #   "name": "ماژول پلاک خوان۲",
    #   "description": "پلاک خوان دوربین گیت۱ برای ورودی/خروجی",
    #   "ip": "185.81.99.23",
    #   "port": 46,
    #   "latitude": "98.0.0",
    #   "longitude": "98.0.0",
    # },
    # {
    #   "name": "ماژول پلاک خوان۳",
    #   "description": "پلاک خوان دوربین گیت۱ برای ورودی",
    #   "ip": "185.81.99.23",
    #   "port": 47,
    #   "latitude": "98.0.0",
    #   "longitude": "98.0.0",
    # },
    # {
    #   "name": "ماژول پلاک خوان۴",
    #   "description": "پلاک خوان دوربین گیت۱ برای خروجی",
    #   "ip": "185.81.99.23",
    #   "port": 48,
    #   "latitude": "98.0.0",
    #   "longitude": "98.0.0",
    # },
    # {
    #   "name": "ماژول پلاک خوان۵",
    #   "description": "پلاک خوان دوربین گیت۲ برای ورودی/خروجی",
    #   "ip": "185.81.99.23",
    #   "port": 49,
    #   "latitude": "98.0.0",
    #   "longitude": "98.0.0",
    # }
]


default_cameras = [
    {
      "name": "دوربین ۱",
      "latitude": "1.0.1",
      "longitude": "1.0.1",
      "description": "دوربین اصلی گیت",
      "gate_id": 1,
      "lpr_id": 1,
    },
    # {
    #   "name": "دوربین دوم",
    #   "latitude": "2.0.1",
    #   "longitude": "2.0.1",
    #   "description": "دوربین گیت ورود",
    #   "gate_id": 1,
    #   "lpr_id": 1,
    # },
    # {
    #   "name": "دوربین سوم",
    #   "latitude": "3.0.1",
    #   "longitude": "3.0.1",
    #   "description": "دوربین گیت خروج",
    #   "gate_id": 1,
    #   "lpr_id": 1,
    # },
    # {
    #   "name": "دوربین گیت اصلی",
    #   "latitude": "4.0.1",
    #   "longitude": "4.0.1",
    #   "description": "دوربین اصلی(ورود/خروج)",
    #   "gate_id": 1,
    #   "lpr_id": 1,
    # },
]



async def create_default_admin(db: AsyncSession):
    if settings.ADMIN_USERNAME:
        user_op = UserOperation(db)
        db_admin = await user_op.get_user_username(settings.ADMIN_USERNAME)
        if db_admin:
            print("Admin user already exists.")
            return

        admin = UserCreate(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password=settings.ADMIN_PASSWORD,
            user_type=UserType.ADMIN
        )
        admin = await user_op.create_user(admin)
        print("Admin user created.")

async def initialize_defaults(db: AsyncSession):

    user_op = UserOperation(db)
    for user in default_users:
        db_user = await user_op.get_user_username(user.get("username"))
        if db_user is None:
            user_obj = UserCreate(
                username=user["username"],
                email=user["email"],
                user_type=user["user_type"],
                password=user["password"],
            )
            new_user = await user_op.create_user(user_obj)
            print(f"Created user with ID: {new_user.id}")
    print("default users created!!!")

    building_op = BuildingOperation(db)
    for building in default_buildings:
        db_building = await building_op.get_one_object_name(building.get("name"))
        if db_building is None:

            building_obj = BuildingCreate(
                name=building["name"],
                description=building["description"],
                latitude=building["latitude"],
                longitude=building["longitude"],
            )
            new_building = await building_op.create_building(building_obj)
            print(f"Created building with ID: {new_building.id}")
    print("default buildings created!!!")

    gate_op = GateOperation(db)
    for gate in default_gates:
        db_gate = await gate_op.get_one_object_name(gate.get("name"))
        if db_gate is None:
            gate_obj = GateCreate(
                name=gate["name"],
                description=gate["description"],
                gate_type=gate["gate_type"],
                building_id=gate["building_id"],
            )
            new_gate = await gate_op.create_gate(gate_obj)
            print(f"Created gate with ID: {new_gate.id}")
    print("default gates created!!!")

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
    for lpr in default_lprs:
        db_lpr = await lpr_op.get_one_object_name(lpr["name"])
        if db_lpr:
            print("lpr object already exists.")
            # print("connecting to twisted ...")
            # await add_connection(db_lpr.id, db_lpr.ip, db_lpr.port, db_lpr.auth_token)
            return
        else:
            lpr_obj = LprCreate(
                name=lpr["name"],
                description=lpr["description"],
                latitude=lpr["latitude"],
                longitude=lpr["longitude"],
                ip=lpr["ip"],
                port=lpr["port"],
            )
            new_lpr = await lpr_op.create_lpr(lpr_obj)
            print(f"Created lpr with ID: {new_lpr.id}")
    print("default lprs created!!!")


    camera_op = CameraOperation(db)
    for camera in default_cameras:
        db_camera = await camera_op.get_one_object_name(camera.get("name"))
        if db_camera:
            print("camera object already exists.")
            print("connecting to twisted ...")
            await add_connection(db, lpr_id=db_camera.lpr_id)
            return
        camera_obj = CameraCreate(
            name=camera["name"],
            description=camera["description"],
            latitude=camera["latitude"],
            longitude=camera["longitude"],
            gate_id=camera["gate_id"],
            lpr_id=camera["lpr_id"],
        )
        new_camera = await camera_op.create_camera(camera_obj)
        print(f"Created camera with ID: {new_camera.id}")
        await add_connection(db, lpr_id=new_camera.lpr_id)
    print("default cameras created!!!")
