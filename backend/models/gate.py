from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table, Text, Float, func
from sqlalchemy import Enum as sqlEnum
from sqlalchemy.orm import relationship
from enum import Enum

from database.engine import Base
from models.association import viewer_gate_access, user_gate_access, guest_gate_access
from models.relay import DBRelay

class GateType(Enum):
    ENTRANCE = 0
    EXIT = 1
    BOTH = 2


class DBGate(Base):
    __tablename__ = 'gates'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True, unique=True)
    gate_type = Column(sqlEnum(GateType), default=GateType.BOTH, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    building_id = Column(Integer, ForeignKey('buildings.id'), nullable=False)
    building = relationship('DBBuilding', back_populates='gates')
    cameras = relationship("DBCamera", back_populates="gate", cascade="all, delete-orphan", lazy="selectin")
    users = relationship("DBUser", secondary=viewer_gate_access, back_populates="gates")
    permitted_users = relationship("DBUser", secondary=user_gate_access, back_populates="accessible_gates", lazy="selectin")
    guests = relationship("DBGuest", secondary=guest_gate_access, back_populates="gates", lazy="selectin")
    relays = relationship("DBRelay", back_populates="gate", lazy="selectin")
