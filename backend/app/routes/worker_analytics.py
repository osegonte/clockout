from typing import List, Optional
from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from pydantic import BaseModel
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.worker import Worker
from app.routes.auth import get_current_user

router = APIRouter()


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class PerformanceMetrics(BaseModel):
    worker_id: int
    worker_name: str
    total_shifts: int
    total_hours_worked: float
    on_time_arrivals: int
    late_arrivals: int
    early_departures: int
    attendance_rate: float
    average_hours_per_shift: float
    last_30_days_hours: float
    performance_score: float
    
    class Config:
        from_attributes = True


class AttendanceRecord(BaseModel):
    id: int
    date: datetime
    clock_in_time: Optional[datetime]
    clock_out_time: Optional[datetime]
    hours_worked: Optional[float]
    site_name: str
    status: str  # present, late, early_departure, absent
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class ActivityLog(BaseModel):
    id: int
    timestamp: datetime
    action: str
    description: str
    performed_by: str
    details: Optional[str]
    
    class Config:
        from_attributes = True


class BulkWorkerCreate(BaseModel):
    workers: List[dict]  # List of worker data


class BulkWorkerUpdate(BaseModel):
    worker_ids: List[int]
    updates: dict  # Fields to update


class WorkerSearchResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    employee_id: str
    phone: Optional[str]
    site_name: str
    is_active: bool
    worker_type: Optional[str]
    status: Optional[str]
    start_date: Optional[date]
    hourly_rate: Optional[float]
    
    class Config:
        from_attributes = True


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def calculate_performance_score(
    attendance_rate: float,
    on_time_rate: float,
    hours_worked: float,
    target_hours: float = 160.0  # ~40 hours/week * 4 weeks
) -> float:
    """
    Calculate performance score (0-100)
    - 40% attendance rate
    - 30% on-time rate
    - 30% hours worked vs target
    """
    hours_score = min(hours_worked / target_hours * 100, 100)
    
    performance_score = (
        (attendance_rate * 0.4) +
        (on_time_rate * 0.3) +
        (hours_score * 0.3)
    )
    
    return round(performance_score, 2)


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/{worker_id}/performance", response_model=PerformanceMetrics)
async def get_worker_performance(
    worker_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for a worker
    
    Calculates:
    - Total shifts and hours
    - Attendance rate
    - On-time arrival rate
    - Performance score
    """
    # Get worker
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Check permissions
    if current_user.organization_id != worker.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get attendance events
    events_query = text("""
        SELECT 
            COUNT(*) as total_shifts,
            SUM(CASE WHEN clock_in_time IS NOT NULL THEN 1 ELSE 0 END) as attended_shifts,
            SUM(CASE 
                WHEN clock_in_time IS NOT NULL 
                AND clock_out_time IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (clock_out_time - clock_in_time)) / 3600.0 
                ELSE 0 
            END) as total_hours,
            SUM(CASE 
                WHEN clock_in_time IS NOT NULL 
                AND clock_in_time <= expected_clock_in 
                THEN 1 
                ELSE 0 
            END) as on_time_arrivals,
            SUM(CASE 
                WHEN clock_in_time IS NOT NULL 
                AND clock_in_time > expected_clock_in 
                THEN 1 
                ELSE 0 
            END) as late_arrivals,
            SUM(CASE 
                WHEN clock_out_time IS NOT NULL 
                AND clock_out_time < expected_clock_out 
                THEN 1 
                ELSE 0 
            END) as early_departures
        FROM attendance_events
        WHERE worker_id = :worker_id
        AND created_at >= :start_date
        AND created_at <= :end_date
        AND deleted_at IS NULL
    """)
    
    result = db.execute(events_query, {
        "worker_id": worker_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchone()
    
    total_shifts = result[0] or 0
    attended_shifts = result[1] or 0
    total_hours = result[2] or 0.0
    on_time_arrivals = result[3] or 0
    late_arrivals = result[4] or 0
    early_departures = result[5] or 0
    
    # Calculate rates
    attendance_rate = (attended_shifts / total_shifts * 100) if total_shifts > 0 else 0
    on_time_rate = (on_time_arrivals / attended_shifts * 100) if attended_shifts > 0 else 0
    avg_hours_per_shift = (total_hours / attended_shifts) if attended_shifts > 0 else 0
    
    # Calculate performance score
    performance_score = calculate_performance_score(
        attendance_rate=attendance_rate,
        on_time_rate=on_time_rate,
        hours_worked=total_hours
    )
    
    # Get last 30 days hours
    last_30_days_query = text("""
        SELECT SUM(EXTRACT(EPOCH FROM (clock_out_time - clock_in_time)) / 3600.0)
        FROM attendance_events
        WHERE worker_id = :worker_id
        AND created_at >= :last_30_days
        AND clock_in_time IS NOT NULL
        AND clock_out_time IS NOT NULL
        AND deleted_at IS NULL
    """)
    
    last_30_result = db.execute(last_30_days_query, {
        "worker_id": worker_id,
        "last_30_days": end_date - timedelta(days=30)
    }).fetchone()
    
    last_30_days_hours = last_30_result[0] or 0.0
    
    return PerformanceMetrics(
        worker_id=worker.id,
        worker_name=worker.name,
        total_shifts=total_shifts,
        total_hours_worked=round(total_hours, 2),
        on_time_arrivals=on_time_arrivals,
        late_arrivals=late_arrivals,
        early_departures=early_departures,
        attendance_rate=round(attendance_rate, 2),
        average_hours_per_shift=round(avg_hours_per_shift, 2),
        last_30_days_hours=round(last_30_days_hours, 2),
        performance_score=performance_score
    )


@router.get("/{worker_id}/attendance", response_model=List[AttendanceRecord])
async def get_worker_attendance(
    worker_id: int,
    days: int = Query(30, description="Number of days of history"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get attendance history for a worker
    
    Returns daily attendance records with clock in/out times
    """
    # Get worker
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Check permissions
    if current_user.organization_id != worker.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get attendance records
    attendance_query = text("""
        SELECT 
            e.id,
            e.created_at as date,
            e.clock_in_time,
            e.clock_out_time,
            CASE 
                WHEN e.clock_in_time IS NOT NULL AND e.clock_out_time IS NOT NULL
                THEN EXTRACT(EPOCH FROM (e.clock_out_time - e.clock_in_time)) / 3600.0
                ELSE NULL
            END as hours_worked,
            s.name as site_name,
            CASE
                WHEN e.clock_in_time IS NULL THEN 'absent'
                WHEN e.clock_in_time > e.expected_clock_in THEN 'late'
                WHEN e.clock_out_time IS NOT NULL AND e.clock_out_time < e.expected_clock_out THEN 'early_departure'
                ELSE 'present'
            END as status,
            e.notes
        FROM attendance_events e
        LEFT JOIN sites s ON e.site_id = s.id
        WHERE e.worker_id = :worker_id
        AND e.created_at >= :start_date
        AND e.created_at <= :end_date
        AND e.deleted_at IS NULL
        ORDER BY e.created_at DESC
    """)
    
    results = db.execute(attendance_query, {
        "worker_id": worker_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()
    
    attendance_records = []
    for row in results:
        attendance_records.append(AttendanceRecord(
            id=row[0],
            date=row[1],
            clock_in_time=row[2],
            clock_out_time=row[3],
            hours_worked=round(row[4], 2) if row[4] else None,
            site_name=row[5] or "Unknown",
            status=row[6],
            notes=row[7]
        ))
    
    return attendance_records


@router.get("/{worker_id}/activity", response_model=List[ActivityLog])
async def get_worker_activity(
    worker_id: int,
    days: int = Query(30, description="Number of days of history"),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get activity log for a worker
    
    Shows all actions performed on this worker record
    """
    # Get worker
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Check permissions
    if current_user.organization_id != worker.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get audit logs
    audit_query = text("""
        SELECT 
            al.id,
            al.timestamp,
            al.action,
            al.description,
            u.full_name as performed_by,
            al.details
        FROM audit_log al
        LEFT JOIN users u ON al.performed_by = u.id
        WHERE al.entity_type = 'worker'
        AND al.entity_id = :worker_id
        AND al.timestamp >= :start_date
        AND al.timestamp <= :end_date
        ORDER BY al.timestamp DESC
        LIMIT :limit
    """)
    
    results = db.execute(audit_query, {
        "worker_id": worker_id,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit
    }).fetchall()
    
    activity_logs = []
    for row in results:
        activity_logs.append(ActivityLog(
            id=row[0],
            timestamp=row[1],
            action=row[2],
            description=row[3],
            performed_by=row[4] or "System",
            details=row[5]
        ))
    
    return activity_logs


@router.post("/bulk-create", status_code=201)
async def bulk_create_workers(
    bulk_data: BulkWorkerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple workers at once
    
    Only admins can bulk create workers
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can bulk create workers")
    
    created_workers = []
    errors = []
    
    for idx, worker_data in enumerate(bulk_data.workers):
        try:
            # Create worker using ACTUAL Worker model fields
            full_name = f"{worker_data.get('first_name', '')} {worker_data.get('last_name', '')}".strip()
            
            new_worker = Worker(
                organization_id=current_user.organization_id,
                site_id=worker_data.get("site_id"),
                name=full_name or worker_data.get("name"),
                employee_id=worker_data.get("employee_id"),
                phone=worker_data.get("phone"),
                is_active=worker_data.get("is_active", True),
                worker_type=worker_data.get("worker_type", "full_time"),
                hourly_rate=worker_data.get("hourly_rate"),
                start_date=worker_data.get("start_date"),
                status=worker_data.get("status", "active"),
                created_by=current_user.id
            )
            
            db.add(new_worker)
            db.flush()  # Get the ID without committing
            
            created_workers.append({
                "index": idx,
                "id": new_worker.id,
                "name": new_worker.name,
                "employee_id": new_worker.employee_id
            })
            
        except Exception as e:
            errors.append({
                "index": idx,
                "error": str(e),
                "data": worker_data
            })
    
    db.commit()
    
    return {
        "message": f"Created {len(created_workers)} workers",
        "created": created_workers,
        "errors": errors,
        "total_attempted": len(bulk_data.workers),
        "successful": len(created_workers),
        "failed": len(errors)
    }


@router.put("/bulk-update", status_code=200)
async def bulk_update_workers(
    bulk_data: BulkWorkerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update multiple workers at once
    
    Only admins can bulk update workers
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can bulk update workers")
    
    updated_workers = []
    errors = []
    
    for worker_id in bulk_data.worker_ids:
        try:
            worker = db.query(Worker).filter(
                Worker.id == worker_id,
                Worker.organization_id == current_user.organization_id,
                Worker.deleted_at.is_(None)
            ).first()
            
            if not worker:
                errors.append({
                    "worker_id": worker_id,
                    "error": "Worker not found or access denied"
                })
                continue
            
            # Update fields
            for key, value in bulk_data.updates.items():
                if hasattr(worker, key):
                    setattr(worker, key, value)
            
            worker.updated_by = current_user.id
            worker.updated_at = datetime.now(timezone.utc)
            
            updated_workers.append({
                "id": worker.id,
                "name": worker.name,
                "employee_id": worker.employee_id
            })
            
        except Exception as e:
            errors.append({
                "worker_id": worker_id,
                "error": str(e)
            })
    
    db.commit()
    
    return {
        "message": f"Updated {len(updated_workers)} workers",
        "updated": updated_workers,
        "errors": errors,
        "total_attempted": len(bulk_data.worker_ids),
        "successful": len(updated_workers),
        "failed": len(errors)
    }


@router.get("/search", response_model=List[WorkerSearchResponse])
async def search_workers(
    query: Optional[str] = Query(None, description="Search by name, employee ID, or phone"),
    site_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    worker_type: Optional[str] = Query(None, description="Filter by worker type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advanced worker search with multiple filters
    
    Can search by:
    - Name, employee ID, phone (fuzzy search)
    - Site
    - Active status
    - Worker type
    - Status
    """
    # Build base query using ACTUAL Worker columns
    search_query = """
        SELECT 
            w.id,
            w.name,
            w.employee_id,
            w.phone,
            s.name as site_name,
            w.is_active,
            w.worker_type,
            w.status,
            w.start_date,
            w.hourly_rate
        FROM workers w
        LEFT JOIN sites s ON w.site_id = s.id
        WHERE w.organization_id = :org_id
        AND w.deleted_at IS NULL
    """
    
    params = {"org_id": current_user.organization_id}
    
    # Add filters
    if query:
        search_query += """
            AND (
                w.name ILIKE :query 
                OR w.employee_id ILIKE :query
                OR w.phone ILIKE :query
            )
        """
        params["query"] = f"%{query}%"
    
    if site_id:
        search_query += " AND w.site_id = :site_id"
        params["site_id"] = site_id
    
    if is_active is not None:
        search_query += " AND w.is_active = :is_active"
        params["is_active"] = is_active
    
    if worker_type:
        search_query += " AND w.worker_type = :worker_type"
        params["worker_type"] = worker_type
    
    if status:
        search_query += " AND w.status = :status"
        params["status"] = status
    
    search_query += " ORDER BY w.name LIMIT :limit"
    params["limit"] = limit
    
    # Execute search
    results = db.execute(text(search_query), params).fetchall()
    
    search_results = []
    for row in results:
        # Split name into first/last for response
        name_parts = row[1].split(' ', 1) if row[1] else ['', '']
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        search_results.append(WorkerSearchResponse(
            id=row[0],
            first_name=first_name,
            last_name=last_name,
            employee_id=row[2],
            phone=row[3],
            site_name=row[4] or "Unassigned",
            is_active=row[5],
            worker_type=row[6],
            status=row[7],
            start_date=row[8],
            hourly_rate=float(row[9]) if row[9] else None
        ))
    
    return search_results