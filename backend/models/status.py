from sqlalchemy import Column, Integer, Boolean, String, DateTime, String, func
from sqlalchemy.orm import relationship

from database.engine import Base

class DBStatus(Base):
    __tablename__ = 'statuses'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    keys = relationship('DBRelayKey', back_populates='status', cascade='all, delete-orphan', lazy="selectin")
