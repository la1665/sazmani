from sqlalchemy import Column, func, Text
from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship

from database.engine import Base

class DBLpr(Base):
    __tablename__ = 'lprs'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True, unique=True)
    ip = Column(String, nullable=False, index=True)
    port = Column(Integer, nullable=False)
    auth_token = Column(String, nullable=False)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    cameras = relationship("DBCamera", back_populates="lpr", cascade="all, delete-orphan", lazy="selectin")
    settings = relationship(
            "DBLprSettingInstance",
            back_populates="lpr",
            lazy="selectin",
            cascade="all, delete-orphan"
        )
