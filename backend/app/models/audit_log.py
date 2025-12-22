from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """Audit trail for all system actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system actions
    action = Column(String(50), nullable=False, index=True)  # login, create, update, delete, etc.
    entity_type = Column(String(50), nullable=False, index=True)  # worker, site, user, etc.
    entity_id = Column(Integer, nullable=True)  # ID of affected entity
    details = Column(JSON, nullable=True)  # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)