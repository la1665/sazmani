"""Add default data initialization

Revision ID: 68273d3b535e
Revises: 47d8cd835256
Create Date: 2024-12-25 00:26:58.417625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from database.engine import Base
from utils.db_utils import (
    default_users,
    default_buildings,
    default_gates,
    default_camera_settings,
    default_lpr_settings,
    default_lprs,
    default_cameras,
)

# revision identifiers, used by Alembic.
revision: str = '68273d3b535e'
down_revision: Union[str, None] = '47d8cd835256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    # Add default buildings
    for building in default_buildings:
        session.execute(
            sa.text(
                """
                INSERT INTO buildings (name, latitude, longitude, description, is_active, created_at, updated_at)
                VALUES (:name, :latitude, :longitude, :description, :is_active, :created_at, :updated_at)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            building,
        )

    # Add default gates
    for gate in default_gates:
        session.execute(
            sa.text(
                """
                INSERT INTO gates (name, description, gate_type, building_id, is_active, created_at, updated_at)
                VALUES (:name, :description, :gate_type, :building_id, :is_active, :created_at, :updated_at)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            gate,
        )

    # Add default camera settings
    for cam_setting in default_camera_settings:
        session.execute(
            sa.text(
                """
                INSERT INTO camera_settings (name, value, setting_type, is_active, created_at, updated_at)
                VALUES (:name, :value, :setting_type, :is_active, :created_at, :updated_at)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            cam_setting,
        )

    # Add default LPR settings
    for lpr_setting in default_lpr_settings:
        session.execute(
            sa.text(
                """
                INSERT INTO lpr_settings (name, value, setting_type, is_active, created_at, updated_at)
                VALUES (:name, :value, :setting_type, :is_active, :created_at, :updated_at)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            lpr_setting,
        )

    # Add default LPRs
    # for lpr in default_lprs:
    #     session.execute(
    #         sa.text(
    #             """
    #             INSERT INTO lprs (name, description, ip, port, auth_token, latitude, longitude, is_active, created_at, updated_at)
    #             VALUES (:name, :description, :ip, :port, :auth_token, :latitude, :longitude, :is_active, :created_at, :updated_at)
    #             ON CONFLICT (name) DO NOTHING
    #             """
    #         ),
    #         lpr,
    #     )

    # # Add default cameras
    # for camera in default_cameras:
    #     session.execute(
    #         sa.text(
    #             """
    #             INSERT INTO cameras (name, description, latitude, longitude, gate_id, lpr_id, is_active, created_at, updated_at)
    #             VALUES (:name, :description, :latitude, :longitude, :gate_id, :lpr_id, :is_active, :created_at, :updated_at)
    #             ON CONFLICT (name) DO NOTHING
    #             """
    #         ),
    #         camera,
    #     )

    session.commit()


def downgrade() -> None:
    pass
