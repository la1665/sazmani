from sqlalchemy import func, Column, Text, ForeignKey
from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship

from database.engine import Base
from models.association import camera_lpr_association

class DBCamera(Base):
    __tablename__ = 'cameras'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False, unique=True)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    gate_id = Column(Integer, ForeignKey('gates.id'), nullable=False)
    gate = relationship("DBGate", back_populates="cameras")
    lpr_id = Column(Integer, ForeignKey("lprs.id"), nullable=False)
    lpr = relationship("DBLpr", back_populates="cameras")
    settings = relationship(
            "DBCameraSettingInstance",
            back_populates="camera",
            lazy="selectin",
            cascade="all, delete-orphan"
        )
