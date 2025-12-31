from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Time, Numeric, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Relationships
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Status and priority
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Status: 'pending', 'in_progress', 'completed', 'cancelled'
    priority = Column(String(20), default="normal")
    # Priority: 'normal', 'urgent'
    
    # Timing
    due_date = Column(Date, index=True)
    due_time = Column(Time)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    estimated_duration_minutes = Column(Integer)
    actual_duration_minutes = Column(Integer)
    
    # Documentation
    worker_notes = Column(Text)
    manager_notes = Column(Text)
    before_photos = Column(JSON, default=[])
    after_photos = Column(JSON, default=[])
    
    # Harvest/quantity tracking
    requires_quantity = Column(Boolean, default=False)
    target_quantity = Column(Numeric(10, 2))
    actual_quantity = Column(Numeric(10, 2))
    quantity_unit = Column(String(20))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships (define in worker.py and user.py too)
    # worker = relationship("Worker", back_populates="tasks")
    # site = relationship("Site")
    # assigner = relationship("User")


class IssueReport(Base):
    __tablename__ = "issue_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    reporter_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Issue details
    issue_type = Column(String(50), nullable=False)
    # Types: 'pest', 'disease', 'equipment', 'weather', 'supply', 'safety', 'other'
    severity = Column(String(20), nullable=False, default="moderate", index=True)
    # Severity: 'minor', 'moderate', 'severe'
    title = Column(String(200))
    description = Column(Text, nullable=False)
    location = Column(String(200))
    
    # Documentation
    photos = Column(JSON, default=[])
    
    # Status tracking
    status = Column(String(20), nullable=False, default="open", index=True)
    # Status: 'open', 'investigating', 'resolved', 'closed'
    assigned_to = Column(Integer, ForeignKey("users.id"))
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    
    # GPS location
    gps_lat = Column(Numeric(10, 8))
    gps_lon = Column(Numeric(11, 8))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutoAttendance(Base):
    __tablename__ = "auto_attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Clock in details
    clock_in_time = Column(DateTime(timezone=True), nullable=False, index=True)
    clock_in_gps_lat = Column(Numeric(10, 8))
    clock_in_gps_lon = Column(Numeric(11, 8))
    clock_in_accuracy_m = Column(Numeric(10, 2))
    auto_clocked_in = Column(Boolean, default=True)
    
    # Clock out details
    clock_out_time = Column(DateTime(timezone=True))
    clock_out_gps_lat = Column(Numeric(10, 8))
    clock_out_gps_lon = Column(Numeric(11, 8))
    clock_out_accuracy_m = Column(Numeric(10, 2))
    auto_clocked_out = Column(Boolean, default=True)
    
    # Calculated fields
    total_hours = Column(Numeric(5, 2))
    is_valid = Column(Boolean, default=True)
    
    # Metadata
    device_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Can be for either user or worker
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Read status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True))
    
    # Related records
    related_task_id = Column(Integer, ForeignKey("tasks.id"))
    related_issue_id = Column(Integer, ForeignKey("issue_reports.id"))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)