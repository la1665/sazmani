from sqlalchemy import Column, func, Enum as sqlalchemyEnum
from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum

from database.engine import Base
from models.association import viewer_gate_access, user_gate_access, guest_gate_access

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

    vehicles = relationship("DBVehicle", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
    gates = relationship("DBGate", secondary=viewer_gate_access, back_populates="users", lazy="selectin")
    accessible_gates = relationship("DBGate", secondary=user_gate_access, back_populates="permitted_users", lazy="selectin")
    guests_invited = relationship("DBGuest", back_populates="inviting_user", cascade="all, delete-orphan", lazy="selectin")


class DBGuest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone_number = Column(String(11), nullable=True)
    user_type = Column(String(11), default="guest", nullable=False)

    # Access period for the guest
    start_date = Column(DateTime, default=func.now(), nullable=False)
    end_date = Column(DateTime, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Reference to the user who invited the guest
    inviting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inviting_user = relationship("DBUser", back_populates="guests_invited")
    # Reference to the vehicle
    vehicles = relationship("DBVehicle", back_populates="guest", cascade="all, delete-orphan", lazy="selectin")
    gates = relationship("DBGate", secondary="guest_gate_access", back_populates="guests", lazy="selectin")
