from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    Text,
    UniqueConstraint,
    Index,
    Enum as sqlalchemyEnum,
    func,
)
from sqlalchemy.orm import relationship
from enum import Enum

from database.engine import Base


# Define an Enum for protocol
class ProtocolEnum(str, Enum):
    TCP = "TCP"
    UDP = "UDP"
    API = "API"


class DBRelay(Base):
    __tablename__ = "relays"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    ip = Column(String, nullable=False, index=True)  # IP address of the relay
    port = Column(Integer, nullable=False)  # Port for communication
    protocol = Column(sqlalchemyEnum(ProtocolEnum), default=ProtocolEnum.API, nullable=False)  # Protocol (TCP, UDP)
    description = Column(Text, nullable=True)  # Optional description of the relay
    number_of_keys = Column(Integer, nullable=False)  # Number of keys the relay can handle
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    # Relationship with Gate
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)  # Foreign key to Gate
    gate = relationship("DBGate", back_populates="relays", lazy="joined")
    keys = relationship('DBRelayKey', back_populates='relay', cascade='all, delete-orphan', lazy="selectin")
