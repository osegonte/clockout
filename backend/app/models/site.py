from sqlalchemy import Column, Integer, String, Float, DateTime, Time, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Geofence
    gps_lat = Column(Float, nullable=False)
    gps_lon = Column(Float, nullable=False)
    radius_m = Column(Float, default=100.0)  # Radius in meters
    
    # Time windows
    checkin_start = Column(Time)  # e.g., 06:00:00
    checkin_end = Column(Time)    # e.g., 10:00:00
    checkout_start = Column(Time) # e.g., 14:00:00
    checkout_end = Column(Time)   # e.g., 20:00:00
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="sites")
    workers = relationship("Worker", back_populates="site")
    clock_events = relationship("ClockEvent", back_populates="site")