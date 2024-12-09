from sqlalchemy import func, Text, Column, Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship

from database.engine import Base


class DBBuilding(Base):
    __tablename__ = 'buildings'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True, unique=True)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    gates = relationship('DBGate', back_populates='building', cascade='all, delete-orphan', lazy="selectin")
