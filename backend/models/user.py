from sqlalchemy import Column, func, Enum as sqlalchemyEnum
from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship
from enum import Enum

from database.engine import Base
from models.association import user_gate_access

class UserType(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"
    VIEWER = "viewer"


class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # username = Column(String(255), unique=True, index=True, nullable=False)
    personal_number = Column(String(255), unique=True, index=True, nullable=False)
    national_id = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    office = Column(String(255), nullable=True)
    phone_number = Column(String(11), nullable=True)
    user_type = Column(sqlalchemyEnum(UserType), default=UserType.USER, nullable=False)
    email = Column(String(255),unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    profile_image = Column(String, nullable=True)
    password_changed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    vehicles = relationship("DBVehicle", back_populates="owner", lazy="selectin")
    gates = relationship("DBGate", secondary=user_gate_access, back_populates="users", lazy="selectin")
