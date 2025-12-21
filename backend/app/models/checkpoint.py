from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Checkpoint(Base):
    """NFC checkpoint locations for future Stage 6"""
    __tablename__ = "checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String)
    checkpoint_type = Column(String(20))  # entry, exit, task, patrol
    
    nfc_tag_id = Column(String(100), unique=True, index=True)
    mobile_nfc_id = Column(String(100))
    
    location_lat = Column(Numeric(10, 8))
    location_lng = Column(Numeric(11, 8))
    radius_m = Column(Numeric(10, 2), default=10.0)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())