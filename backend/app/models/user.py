from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    # ✅ STAGE 1: Owner information
    owner_name = Column(String(200))
    owner_email = Column(String(200))
    owner_phone = Column(String(20))
    
    # ✅ STAGE 1: Subscription management
    subscription_plan = Column(String(50), default='free')
    subscription_status = Column(String(20), default='trial')
    subscription_start_date = Column(DateTime(timezone=True), default=func.now())
    subscription_end_date = Column(DateTime(timezone=True))
    
    # ✅ STAGE 1: Plan limits
    max_sites = Column(Integer, default=1)
    max_workers = Column(Integer, default=10)
    max_managers = Column(Integer, default=2)
    
    # ✅ STAGE 1: Soft delete
    deleted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sites = relationship("Site", back_populates="organization")
    users = relationship("User", back_populates="organization")
    workers = relationship("Worker", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False)  # admin, manager (legacy)
    user_mode = Column(String, default="manager")  # manager, admin
    is_active = Column(Boolean, default=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # ✅ STAGE 1: Role system
    role_id = Column(Integer, ForeignKey("roles.id"))
    
    # ✅ STAGE 1: Audit fields
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # ✅ STAGE 1: Soft delete
    deleted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    # Note: role relationship will be added once we create the Role model