from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class UserSite(Base):
    """Junction table for manager-to-site assignments"""
    __tablename__ = "user_sites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())