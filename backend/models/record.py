from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database.engine import Base

class DBRecord(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    camera_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    video_url = Column(String, nullable=False)




class DBScheduledRecord(Base):
    __tablename__ = "scheduled_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    camera_id = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)  # Scheduled start time
    duration = Column(Integer, nullable=False)  # Duration of the recording
    is_processed = Column(Boolean, default=False)  # Indicates if the recording has been processed
