from sqlalchemy import Column, String, Integer, Float,ForeignKey, DateTime, func

from database.engine import Base


class DBTraffic(Base):
    __tablename__ = "traffic"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, index=True)
    timestamp = Column(DateTime, default=func.now())
    ocr_accuracy = Column(Float, nullable=True)
    vision_speed = Column(Float, nullable=True)
    camera_id = Column(Integer, index=True)
    gate_id = Column(Integer, index=True)
    # gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    # camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)

    # vehicles = relationship(
    #     "DBVehicle",
    #     secondary="traffic_vehicle_association",
    #     back_populates="traffic_events"
    # )
