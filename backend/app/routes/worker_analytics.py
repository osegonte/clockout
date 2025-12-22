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
    employee_id: Optional[str]  # Can be NULL
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
    
    Note: Returns zeroed metrics until attendance_events table is created in future stage
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
    
    # Return zeroed metrics (attendance_events table doesn't exist yet)
    # This will be implemented in a future stage when attendance tracking is added
    return PerformanceMetrics(
        worker_id=worker.id,
        worker_name=worker.name,
        total_shifts=0,
        total_hours_worked=0.0,
        on_time_arrivals=0,
        late_arrivals=0,
        early_departures=0,
        attendance_rate=0.0,
        average_hours_per_shift=0.0,
        last_30_days_hours=0.0,
        performance_score=0.0
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
    
    Note: Returns empty list until attendance_events table is created in future stage
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
    
    # Return empty list (attendance_events table doesn't exist yet)
    # This will be implemented in a future stage when attendance tracking is added
    return []


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
    
    Note: Returns empty list until audit_log table is created in future stage
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
    
    # Return empty list (audit_log table doesn't exist yet)
    # This will be implemented in a future stage when audit logging is added
    return []


@router.post("/bulk-create", status_code=201)
async def bulk_create_workers(
    bulk_data: BulkWorkerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple workers at once
    
    Only admins can bulk create workers
    Skips workers with duplicate employee_id gracefully
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can bulk create workers")
    
    created_workers = []
    errors = []
    
    for idx, worker_data in enumerate(bulk_data.workers):
        try:
            # Check for duplicate employee_id first
            employee_id = worker_data.get("employee_id")
            if employee_id:
                existing = db.query(Worker).filter(
                    Worker.employee_id == employee_id,
                    Worker.deleted_at.is_(None)
                ).first()
                
                if existing:
                    errors.append({
                        "index": idx,
                        "error": f"Worker with employee_id '{employee_id}' already exists (ID: {existing.id})",
                        "data": worker_data
                    })
                    continue  # Skip this worker
            
            # Create worker using ACTUAL Worker model fields
            full_name = f"{worker_data.get('first_name', '')} {worker_data.get('last_name', '')}".strip()
            
            new_worker = Worker(
                organization_id=current_user.organization_id,
                site_id=worker_data.get("site_id"),
                name=full_name or worker_data.get("name"),
                employee_id=employee_id,
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
            db.rollback()  # Rollback on error to prevent PendingRollbackError
            errors.append({
                "index": idx,
                "error": str(e),
                "data": worker_data
            })
    
    # Only commit if we created at least one worker
    if created_workers:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to commit workers: {str(e)}"
            )
    
    return {
        "message": f"Created {len(created_workers)} workers, skipped {len(errors)} duplicates/errors",
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
            employee_id=row[2] or "",  # Provide default empty string for NULL
            phone=row[3],
            site_name=row[4] or "Unassigned",
            is_active=row[5],
            worker_type=row[6],
            status=row[7],
            start_date=row[8],
            hourly_rate=float(row[9]) if row[9] else None
        ))
    
    return search_results