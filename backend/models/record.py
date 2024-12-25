from sqlalchemy import Column, Integer, String, DateTime

from database.engine import Base

class DBRecord(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    camera_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    video_url = Column(String, nullable=False)
