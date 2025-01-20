from sqlalchemy import Column, Integer, ForeignKey, Time, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from database.engine import Base

class DBRelayKey(Base):
    __tablename__ = 'keys'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key_number = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    relay_id = Column(Integer, ForeignKey('relays.id'), nullable=False)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=True)
    status_id = Column(Integer, ForeignKey('statuses.id'), nullable=False)
    relay = relationship('DBRelay', back_populates='keys', lazy="joined")
    camera = relationship('DBCamera',  back_populates='keys', lazy="selectin")
    status = relationship('DBStatus', back_populates='keys', lazy="selectin")
