from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, date, timedelta
from decimal import Decimal
import math
from app.database import get_db
from app.models.task import AutoAttendance
from app.models.worker import Worker
from app.models.site import Site
from app.schemas.task import (
    AttendanceClockInRequest, AttendanceClockOutRequest,
    AttendanceResponse, AttendanceSummaryResponse
)
from app.routes.worker_auth import get_current_worker

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.
    Returns distance in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance


@router.post("/clock-in", response_model=AttendanceResponse)
async def clock_in(
    clock_in_data: AttendanceClockInRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Clock in worker - validates GPS location against site geofence.
    Can be auto (geofence triggered) or manual.
    """
    # Check if already clocked in today
    existing_attendance = db.query(AutoAttendance).filter(
        AutoAttendance.worker_id == current_worker.id,
        func.date(AutoAttendance.clock_in_time) == date.today(),
        AutoAttendance.clock_out_time == None
    ).first()
    
    if existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already clocked in. Clock out first."
        )
    
    # Get site details
    site = db.query(Site).filter(Site.id == clock_in_data.site_id).first()
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Validate GPS location is within geofence
    distance = calculate_distance(
        float(clock_in_data.gps_lat),
        float(clock_in_data.gps_lon),
        float(site.gps_lat),
        float(site.gps_lon)
    )
    
    is_valid = distance <= float(site.radius_m)
    
    if not is_valid and clock_in_data.auto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location outside geofence. Distance: {int(distance)}m, Required: {site.radius_m}m"
        )
    
    # Create attendance record
    attendance = AutoAttendance(
        worker_id=current_worker.id,
        site_id=clock_in_data.site_id,
        organization_id=current_worker.organization_id,
        clock_in_time=datetime.utcnow(),
        clock_in_gps_lat=clock_in_data.gps_lat,
        clock_in_gps_lon=clock_in_data.gps_lon,
        clock_in_accuracy_m=clock_in_data.accuracy_m,
        auto_clocked_in=clock_in_data.auto,
        device_id=clock_in_data.device_id,
        is_valid=is_valid
    )
    
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    
    # TODO: Send notification to worker
    
    return enrich_attendance_response(attendance, db)


@router.post("/clock-out", response_model=AttendanceResponse)
async def clock_out(
    clock_out_data: AttendanceClockOutRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Clock out worker - validates GPS and calculates total hours.
    Can be auto (geofence triggered) or manual.
    """
    # Find today's open attendance record
    attendance = db.query(AutoAttendance).filter(
        AutoAttendance.worker_id == current_worker.id,
        func.date(AutoAttendance.clock_in_time) == date.today(),
        AutoAttendance.clock_out_time == None
    ).first()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active clock-in found. Clock in first."
        )
    
    # Get site details for geofence validation
    site = db.query(Site).filter(Site.id == attendance.site_id).first()
    
    # Validate GPS (for auto clock-out)
    if clock_out_data.auto and site:
        distance = calculate_distance(
            float(clock_out_data.gps_lat),
            float(clock_out_data.gps_lon),
            float(site.gps_lat),
            float(site.gps_lon)
        )
        
        # For clock-out, we're checking if they're OUTSIDE the geofence
        # If auto is True, they should be outside
        if distance <= float(site.radius_m):
            # Still inside geofence, probably shouldn't auto-clock-out
            pass  # But we'll allow it
    
    # Update attendance record
    attendance.clock_out_time = datetime.utcnow()
    attendance.clock_out_gps_lat = clock_out_data.gps_lat
    attendance.clock_out_gps_lon = clock_out_data.gps_lon
    attendance.clock_out_accuracy_m = clock_out_data.accuracy_m
    attendance.auto_clocked_out = clock_out_data.auto
    
    # Calculate total hours
    duration = (attendance.clock_out_time - attendance.clock_in_time).total_seconds() / 3600
    attendance.total_hours = Decimal(str(round(duration, 2)))
    
    attendance.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(attendance)
    
    # TODO: Send notification to worker with summary
    
    return enrich_attendance_response(attendance, db)


@router.get("/my/today", response_model=AttendanceResponse)
async def get_today_attendance(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get today's attendance record for current worker.
    """
    attendance = db.query(AutoAttendance).filter(
        AutoAttendance.worker_id == current_worker.id,
        func.date(AutoAttendance.clock_in_time) == date.today()
    ).first()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance record for today"
        )
    
    return enrich_attendance_response(attendance, db)


@router.get("/my/history", response_model=List[AttendanceResponse])
async def get_attendance_history(
    start_date: date = None,
    end_date: date = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get attendance history for current worker.
    """
    query = db.query(AutoAttendance).filter(
        AutoAttendance.worker_id == current_worker.id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(func.date(AutoAttendance.clock_in_time) >= start_date)
    
    if end_date:
        query = query.filter(func.date(AutoAttendance.clock_in_time) <= end_date)
    
    # Order by most recent first
    query = query.order_by(AutoAttendance.clock_in_time.desc())
    
    attendance_records = query.limit(limit).all()
    
    return [enrich_attendance_response(record, db) for record in attendance_records]


@router.get("/my/summary/week", response_model=AttendanceSummaryResponse)
async def get_weekly_summary(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get weekly attendance summary for current worker.
    """
    # Calculate start of week (Monday)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    return get_attendance_summary(
        worker_id=current_worker.id,
        start_date=week_start,
        end_date=today,
        period="week",
        db=db
    )


@router.get("/my/summary/month", response_model=AttendanceSummaryResponse)
async def get_monthly_summary(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get monthly attendance summary for current worker.
    """
    # Start of current month
    today = date.today()
    month_start = today.replace(day=1)
    
    return get_attendance_summary(
        worker_id=current_worker.id,
        start_date=month_start,
        end_date=today,
        period="month",
        db=db
    )


@router.post("/manual/clock-in", response_model=AttendanceResponse)
async def manual_clock_in(
    clock_in_data: AttendanceClockInRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Manual clock-in for exceptions (GPS issues, coming on off-day, etc.)
    """
    clock_in_data.auto = False
    return await clock_in(clock_in_data, db, current_worker)


@router.post("/manual/clock-out", response_model=AttendanceResponse)
async def manual_clock_out(
    clock_out_data: AttendanceClockOutRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Manual clock-out for exceptions.
    """
    clock_out_data.auto = False
    return await clock_out(clock_out_data, db, current_worker)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def enrich_attendance_response(attendance: AutoAttendance, db: Session) -> AttendanceResponse:
    """Add computed fields to attendance response"""
    worker = db.query(Worker).filter(Worker.id == attendance.worker_id).first()
    site = db.query(Site).filter(Site.id == attendance.site_id).first()
    
    attendance_dict = AttendanceResponse.model_validate(attendance).model_dump()
    attendance_dict['worker_name'] = worker.name if worker else None
    attendance_dict['site_name'] = site.name if site else None
    
    return AttendanceResponse(**attendance_dict)


def get_attendance_summary(
    worker_id: int,
    start_date: date,
    end_date: date,
    period: str,
    db: Session
) -> AttendanceSummaryResponse:
    """Calculate attendance summary for a date range"""
    from app.models.task import Task
    
    # Get worker
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    # Count days present
    days_present = db.query(
        func.count(func.distinct(func.date(AutoAttendance.clock_in_time)))
    ).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time).between(start_date, end_date)
    ).scalar() or 0
    
    # Sum total hours
    total_hours = db.query(
        func.sum(AutoAttendance.total_hours)
    ).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time).between(start_date, end_date)
    ).scalar() or Decimal('0')
    
    # Calculate average
    avg_hours = total_hours / days_present if days_present > 0 else Decimal('0')
    
    # Count completed tasks in period
    tasks_completed = db.query(Task).filter(
        Task.worker_id == worker_id,
        Task.status == 'completed',
        func.date(Task.completed_at).between(start_date, end_date)
    ).count()
    
    # Count total assigned tasks in period
    total_tasks = db.query(Task).filter(
        Task.worker_id == worker_id,
        func.date(Task.created_at).between(start_date, end_date),
        Task.deleted_at == None
    ).count()
    
    completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
    
    return AttendanceSummaryResponse(
        worker_id=worker_id,
        worker_name=worker.name,
        period=period,
        days_present=days_present,
        total_hours=total_hours,
        avg_hours_per_day=avg_hours,
        tasks_completed=tasks_completed,
        completion_rate=round(completion_rate, 1)
    )