from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from database.engine import Base

class DBVehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, unique=True, index=True)
    vehicle_class = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=True)
    vehicle_color = Column(String, nullable=True)
    car_image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("DBUser", back_populates="vehicles")
