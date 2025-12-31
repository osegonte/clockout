from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Worker(Base):
    __tablename__ = "workers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, index=True)
    employee_id = Column(String, unique=True, index=True)
    
    # 🆕 NEW: Link to user account for worker login
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"))  # Primary site (can be null)
    is_active = Column(Boolean, default=True)
    
    # Employment details
    worker_type = Column(String(50), default='full_time')  # full_time, part_time, seasonal, contract
    hourly_rate = Column(Numeric(10, 2))  # Decimal for money
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default='active')  # active, suspended, terminated, on_leave
    
    # Photo for future facial recognition
    photo_url = Column(String)
    
    # 🆕 NEW: Last login timestamp for worker app
    last_login = Column(DateTime(timezone=True))
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="workers")
    site = relationship("Site", back_populates="workers")
    clock_events = relationship("ClockEvent", back_populates="worker")
    
    # 🆕 NEW: Relationship to user account
    user = relationship("User", foreign_keys=[user_id])
    
    # 🆕 NEW: Relationships to new tables
    # tasks = relationship("Task", back_populates="worker")
    # attendance_records = relationship("AutoAttendance", back_populates="worker")
    # issue_reports = relationship("IssueReport", back_populates="reporter")