from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy import Enum as sqlEnum
from sqlalchemy.orm import relationship
from enum import Enum

from database.engine import Base


class SettingType(Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"


class DBCameraSetting(Base):
    __tablename__ = 'camera_settings'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    description = Column(Text, nullable=True)
    value = Column(String(255), nullable=False)
    setting_type = Column(sqlEnum(SettingType),default=SettingType.STRING, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class DBCameraSettingInstance(Base):
    __tablename__ = 'camera_setting_instances'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    value = Column(String(255), nullable=False)
    setting_type = Column(
        sqlEnum(SettingType), default=SettingType.STRING, nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)
    camera = relationship("DBCamera", back_populates="settings", lazy="selectin")
    default_setting_id = Column(Integer, ForeignKey('camera_settings.id'), nullable=True)
    default_setting = relationship("DBCameraSetting", lazy="selectin")
