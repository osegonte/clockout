from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    device_name = Column(String)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_sync = Column(DateTime(timezone=True))
    
    clock_events = relationship("ClockEvent", back_populates="device")


class ClockEvent(Base):
    __tablename__ = "clock_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    event_type = Column(String, nullable=False)
    
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    
    gps_lat = Column(Float, nullable=False)
    gps_lon = Column(Float, nullable=False)
    accuracy_m = Column(Float)
    
    is_valid = Column(Boolean, default=True)
    distance_m = Column(Float)
    
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String, default="GPS")
    
    worker = relationship("Worker", back_populates="clock_events")
    site = relationship("Site", back_populates="clock_events")
    device = relationship("Device", back_populates="clock_events")
    
    __table_args__ = (
        Index('idx_site_timestamp', 'site_id', 'event_timestamp'),
        Index('idx_worker_timestamp', 'worker_id', 'event_timestamp'),
        Index('idx_event_timestamp', 'event_timestamp'),
    )