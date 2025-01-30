from search_service.search import BaseSearchService

from schema.user import  UserMeilisearch
from schema.guest import GuestMeilisearch
from schema.building import BuildingMeilisearch
from schema.gate import GateMeilisearch
from schema.camera import CameraMeilisearch
from schema.lpr import LprMeilisearch
from schema.traffic import TrafficMeilisearch


# User Search Service
user_search = BaseSearchService[UserMeilisearch](
    index_name="users",
    schema_model=UserMeilisearch,
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
guest_search = BaseSearchService[GuestMeilisearch](
    index_name="guests",
    schema_model=GuestMeilisearch,
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

# Building Search Service
building_search = BaseSearchService[BuildingMeilisearch](
    index_name="buildings",
    schema_model=BuildingMeilisearch,
    searchable_attributes=["name", "description"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Gate Search Service
gate_search = BaseSearchService[GateMeilisearch](
    index_name="gates",
    schema_model=GateMeilisearch,
    searchable_attributes=["name", "description"],
    filterable_attributes=["gate_type", "is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Camera Search Service
camera_search = BaseSearchService[CameraMeilisearch](
    index_name="cameras",
    schema_model=CameraMeilisearch,
    searchable_attributes=["name", "description"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Lpr Search Service
lpr_search = BaseSearchService[LprMeilisearch](
    index_name="lprs",
    schema_model=LprMeilisearch,
    searchable_attributes=["name", "description", "ip"],
    filterable_attributes=["is_active", "created_at", "updated_at"],
    sortable_attributes=["created_at", "updated_at"]
)

# Traffic Search Service
traffic_search = BaseSearchService[TrafficMeilisearch](
    index_name="traffics",
    schema_model=TrafficMeilisearch,
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
