from search_service.search import BaseSearchService

from schema.user import  UserInDB
from schema.guest import GuestInDB
from schema.vehicle import VehicleInDB
from schema.building import BuildingInDB
from schema.gate import GateInDB
from schema.camera import CameraInDB
from schema.camera_setting import CameraSettingInstanceInDB
from schema.lpr import LprInDB
from schema.lpr_setting import LprSettingInstanceInDB
from schema.traffic import TrafficInDB


# User Search Service
user_search = BaseSearchService[UserInDB](
    index_name="users",
    schema_model=UserInDB,
    searchable_attributes=[
        "personal_number",
        "first_name",
        "last_name",
        "national_id",
        "email",
        "phone_number"
    ],
    filterable_attributes=["user_type", "is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Guest Search Service
guest_search = BaseSearchService[GuestInDB](
    index_name="guests",
    schema_model=GuestInDB,
    searchable_attributes=[
        "personal_number",
        "national_id",
        "first_name",
        "last_name",
        "phone_number",
    ],
    filterable_attributes=["user_type", "is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)


vehicle_search = BaseSearchService[VehicleInDB](
    index_name="vehicles",
    schema_model=VehicleInDB,
    searchable_attributes=[
        "plate_number",
        "vehicle_class",
        "vehicle_type",
        "vehicle_color"
    ],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)


# Building Search Service
building_search = BaseSearchService[BuildingInDB](
    index_name="buildings",
    schema_model=BuildingInDB,
    searchable_attributes=["name", "description"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Gate Search Service
gate_search = BaseSearchService[GateInDB](
    index_name="gates",
    schema_model=GateInDB,
    searchable_attributes=["name", "description"],
    filterable_attributes=["gate_type", "is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Camera Search Service
camera_search = BaseSearchService[CameraInDB](
    index_name="cameras",
    schema_model=CameraInDB,
    searchable_attributes=["name", "description"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Camera Setting Instance Search Service
camera_setting_search = BaseSearchService[CameraSettingInstanceInDB](
    index_name="camera_settings",
    schema_model=CameraSettingInstanceInDB,
    searchable_attributes=[
        "name",
        "description",
        "value"
    ],
    filterable_attributes=[
        "setting_type", "is_active", "created_at", "updated_at", "camera_id"
    ],
    sortable_attributes=[
        "created_at", "updated_at"
    ]
)

# Lpr Search Service
lpr_search = BaseSearchService[LprInDB](
    index_name="lprs",
    schema_model=LprInDB,
    searchable_attributes=["name", "description", "ip"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Lpr Setting Instance Search Service
lpr_setting_search = BaseSearchService[LprSettingInstanceInDB](
    index_name="lpr_settings",
    schema_model=LprSettingInstanceInDB,
    searchable_attributes=[
        "name",
        "description",
        "value"
    ],
    filterable_attributes=[
        "setting_type", "is_active", "created_at", "updated_at", "lpr_id"
    ],
    sortable_attributes=[
        "created_at", "updated_at"
    ]
)

# Traffic Search Service
traffic_search = BaseSearchService[TrafficInDB](
    index_name="traffics",
    schema_model=TrafficInDB,
    searchable_attributes=[
        "prefix_2",
        "alpha",
        "mid_3",
        "suffix_2",
        "plate_number",
        "gate_name",
        "camera_name",
        "access_granted"
    ],
    filterable_attributes=["gate_name", "camera_name"],
    sortable_attributes=["timestamp"]
)
