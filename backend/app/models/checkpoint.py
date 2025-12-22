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
    qr_code = Column(String(100))  # Added QR code support
    
    # GPS coordinates (renamed for API consistency)
    gps_lat = Column(Numeric(10, 8))
    gps_lon = Column(Numeric(11, 8))
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Soft delete support
    deleted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())