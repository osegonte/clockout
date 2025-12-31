from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal

# ==========================================
# TASK SCHEMAS
# ==========================================

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = Field(default="normal", pattern="^(normal|urgent)$")
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    manager_notes: Optional[str] = None
    requires_quantity: bool = False
    target_quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None


class TaskCreate(TaskBase):
    worker_id: int
    site_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(normal|urgent)$")
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    manager_notes: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")


class TaskStartRequest(BaseModel):
    """Worker starts a task"""
    pass  # No additional data needed, just mark as started


class TaskCompleteRequest(BaseModel):
    """Worker completes a task"""
    worker_notes: Optional[str] = None
    actual_quantity: Optional[Decimal] = None
    after_photos: Optional[List[str]] = []


class TaskResponse(TaskBase):
    id: int
    worker_id: int
    site_id: int
    assigned_by: int
    organization_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    worker_notes: Optional[str] = None
    before_photos: List[str] = []
    after_photos: List[str] = []
    actual_quantity: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    # Additional computed fields
    worker_name: Optional[str] = None
    site_name: Optional[str] = None
    assigned_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==========================================
# ISSUE REPORT SCHEMAS
# ==========================================

class IssueReportBase(BaseModel):
    issue_type: str = Field(..., pattern="^(pest|disease|equipment|weather|supply|safety|other)$")
    severity: str = Field(default="moderate", pattern="^(minor|moderate|severe)$")
    title: Optional[str] = Field(None, max_length=200)
    description: str = Field(..., min_length=1)
    location: Optional[str] = Field(None, max_length=200)
    gps_lat: Optional[Decimal] = None
    gps_lon: Optional[Decimal] = None


class IssueReportCreate(IssueReportBase):
    site_id: int
    photos: Optional[List[str]] = []


class IssueReportUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|investigating|resolved|closed)$")
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None


class IssueReportResponse(IssueReportBase):
    id: int
    reporter_id: int
    site_id: int
    organization_id: int
    status: str
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    photos: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    # Additional computed fields
    reporter_name: Optional[str] = None
    site_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==========================================
# AUTO ATTENDANCE SCHEMAS
# ==========================================

class AttendanceClockInRequest(BaseModel):
    """Auto clock-in when worker enters geofence"""
    site_id: int
    gps_lat: Decimal
    gps_lon: Decimal
    accuracy_m: Optional[float] = None
    device_id: Optional[str] = None
    auto: bool = True  # False if manual override


class AttendanceClockOutRequest(BaseModel):
    """Auto clock-out when worker leaves geofence"""
    gps_lat: Decimal
    gps_lon: Decimal
    accuracy_m: Optional[float] = None
    auto: bool = True


class AttendanceResponse(BaseModel):
    id: int
    worker_id: int
    site_id: int
    organization_id: int
    clock_in_time: datetime
    clock_in_gps_lat: Optional[Decimal] = None
    clock_in_gps_lon: Optional[Decimal] = None
    auto_clocked_in: bool
    clock_out_time: Optional[datetime] = None
    clock_out_gps_lat: Optional[Decimal] = None
    clock_out_gps_lon: Optional[Decimal] = None
    auto_clocked_out: Optional[bool] = None
    total_hours: Optional[Decimal] = None
    is_valid: bool
    created_at: datetime
    
    # Additional fields
    worker_name: Optional[str] = None
    site_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AttendanceSummaryResponse(BaseModel):
    """Weekly/monthly summary for worker"""
    worker_id: int
    worker_name: str
    period: str  # 'week', 'month'
    days_present: int
    total_hours: Decimal
    avg_hours_per_day: Decimal
    tasks_completed: int
    completion_rate: float  # Percentage


# ==========================================
# NOTIFICATION SCHEMAS
# ==========================================

class NotificationCreate(BaseModel):
    notification_type: str
    title: str = Field(..., max_length=200)
    message: str
    worker_id: Optional[int] = None
    user_id: Optional[int] = None
    related_task_id: Optional[int] = None
    related_issue_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    related_task_id: Optional[int] = None
    related_issue_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# ==========================================
# WORKER AUTH SCHEMAS
# ==========================================

class WorkerLoginRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=4)


class WorkerRegisterRequest(BaseModel):
    """Admin/Manager creates worker with login credentials"""
    employee_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = None
    site_id: int


class WorkerAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    worker: dict  # Worker details including id, name, employee_id, site_id


# ==========================================
# DASHBOARD/STATS SCHEMAS
# ==========================================

class WorkerDashboardResponse(BaseModel):
    """Complete dashboard data for worker app"""
    # Today's stats
    clocked_in: bool
    clock_in_time: Optional[datetime] = None
    hours_today: Decimal
    hours_this_week: Decimal
    
    # Tasks
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks_today: int
    total_tasks_today: int
    
    # This month
    days_worked_this_month: int
    total_hours_this_month: Decimal
    tasks_completed_this_month: int
    completion_rate: float
    
    # Site info
    site_id: int
    site_name: str
    site_gps_lat: Decimal
    site_gps_lon: Decimal
    site_radius_m: Decimal