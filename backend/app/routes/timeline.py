"""
Stage 2.5: Timeline/History API
Track worker check-in/out history and site activity
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.event import ClockEvent
from app.models.worker import Worker
from app.models.site import Site
from app.models.user import User
from app.routes.auth import get_current_user


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class TimelineEventResponse(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    site_id: int
    site_name: str
    event_type: str  # IN or OUT
    event_timestamp: datetime
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    accuracy_m: Optional[float]
    distance_m: Optional[float]
    is_valid: bool
    checkpoint_id: Optional[int]
    checkpoint_name: Optional[str]

    class Config:
        from_attributes = True


class WorkerHistoryResponse(BaseModel):
    worker_id: int
    worker_name: str
    period: dict
    total_check_ins: int
    total_check_outs: int
    total_days_present: int
    total_hours_worked: float
    average_hours_per_day: float
    events: List[TimelineEventResponse]


class SiteActivityResponse(BaseModel):
    site_id: int
    site_name: str
    period: dict
    total_events: int
    unique_workers: int
    total_hours_worked: float
    busiest_day: Optional[dict]
    events: List[TimelineEventResponse]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def can_access_worker(user: User, worker_id: int, db: Session) -> bool:
    """Check if user can access this worker's data"""
    if user.organization_id == 1:  # Super admin
        return True
    
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        return False
    
    if worker.organization_id != user.organization_id:
        return False
    
    if user.role == "admin":
        return True
    
    if user.role == "manager":
        # Check if manager is assigned to worker's site
        from app.models.user import user_sites
        assigned = db.query(user_sites).filter(
            user_sites.c.user_id == user.id,
            user_sites.c.site_id == worker.site_id
        ).first()
        return assigned is not None
    
    return False


def can_access_site(user: User, site_id: int, db: Session) -> bool:
    """Check if user can access this site"""
    if user.organization_id == 1:
        return True
    
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site or site.organization_id != user.organization_id:
        return False
    
    if user.role == "admin":
        return True
    
    if user.role == "manager":
        from app.models.user import user_sites
        assigned = db.query(user_sites).filter(
            user_sites.c.user_id == user.id,
            user_sites.c.site_id == site_id
        ).first()
        return assigned is not None
    
    return False


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/worker/{worker_id}", response_model=WorkerHistoryResponse)
async def get_worker_history(
    worker_id: int,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete check-in/out history for a worker.
    
    **Use cases:**
    - Review worker attendance over time
    - Calculate hours worked
    - Verify GPS locations
    - Audit trail for payroll
    
    **Permissions:**
    - Managers see workers at assigned sites
    - Admins see all workers in their org
    """
    # Check permissions
    if not can_access_worker(current_user, worker_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this worker's history"
        )
    
    # Get worker
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Build query
    query = db.query(ClockEvent).filter(ClockEvent.worker_id == worker_id)
    
    # Date filters
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ClockEvent.event_timestamp >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    else:
        # Default to last 30 days
        start_dt = datetime.utcnow() - timedelta(days=30)
        query = query.filter(ClockEvent.event_timestamp >= start_dt)
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ClockEvent.event_timestamp < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    else:
        end_dt = datetime.utcnow()
    
    # Get events
    events = query.order_by(ClockEvent.event_timestamp.desc()).limit(limit).all()
    
    # Calculate statistics
    check_ins = [e for e in events if e.event_type == "IN"]
    check_outs = [e for e in events if e.event_type == "OUT"]
    
    # Calculate days present (unique dates with check-ins)
    unique_dates = set()
    for event in check_ins:
        unique_dates.add(event.event_timestamp.date())
    
    # Calculate total hours
    total_hours = 0.0
    for date in unique_dates:
        date_check_ins = [e for e in check_ins if e.event_timestamp.date() == date]
        date_check_outs = [e for e in check_outs if e.event_timestamp.date() == date]
        
        if date_check_ins and date_check_outs:
            # Get first check-in and last check-out
            first_in = min(date_check_ins, key=lambda x: x.event_timestamp)
            last_out = max(date_check_outs, key=lambda x: x.event_timestamp)
            
            hours = (last_out.event_timestamp - first_in.event_timestamp).total_seconds() / 3600
            total_hours += hours
    
    avg_hours = total_hours / len(unique_dates) if unique_dates else 0.0
    
    # Build event responses
    event_responses = []
    for event in events:
        site = db.query(Site).filter(Site.id == event.site_id).first()
        
        checkpoint_name = None
        if event.checkpoint_id:
            from app.models.checkpoint import Checkpoint
            checkpoint = db.query(Checkpoint).filter(Checkpoint.id == event.checkpoint_id).first()
            if checkpoint:
                checkpoint_name = checkpoint.name
        
        event_responses.append(TimelineEventResponse(
            id=event.id,
            worker_id=event.worker_id,
            worker_name=worker.name,
            site_id=event.site_id,
            site_name=site.name if site else "Unknown",
            event_type=event.event_type,
            event_timestamp=event.event_timestamp,
            gps_lat=event.gps_lat,
            gps_lon=event.gps_lon,
            accuracy_m=event.accuracy_m,
            distance_m=event.distance_m,
            is_valid=event.is_valid,
            checkpoint_id=event.checkpoint_id,
            checkpoint_name=checkpoint_name
        ))
    
    return WorkerHistoryResponse(
        worker_id=worker.id,
        worker_name=worker.name,
        period={
            "start_date": start_dt.strftime("%Y-%m-%d") if start_date else (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d") if end_date else datetime.utcnow().strftime("%Y-%m-%d")
        },
        total_check_ins=len(check_ins),
        total_check_outs=len(check_outs),
        total_days_present=len(unique_dates),
        total_hours_worked=round(total_hours, 2),
        average_hours_per_day=round(avg_hours, 2),
        events=event_responses
    )


@router.get("/site/{site_id}", response_model=SiteActivityResponse)
async def get_site_activity(
    site_id: int,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get activity timeline for a site.
    
    **Use cases:**
    - Monitor site activity over time
    - Identify busiest days
    - Track unique visitors
    - Analyze traffic patterns
    """
    # Check permissions
    if not can_access_site(current_user, site_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this site's activity"
        )
    
    # Get site
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Build query
    query = db.query(ClockEvent).filter(ClockEvent.site_id == site_id)
    
    # Date filters
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ClockEvent.event_timestamp >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    else:
        start_dt = datetime.utcnow() - timedelta(days=30)
        query = query.filter(ClockEvent.event_timestamp >= start_dt)
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ClockEvent.event_timestamp < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    else:
        end_dt = datetime.utcnow()
    
    # Get all events for stats
    all_events = query.all()
    
    # Get limited events for response
    events = query.order_by(ClockEvent.event_timestamp.desc()).limit(limit).all()
    
    # Calculate statistics
    unique_workers = set(e.worker_id for e in all_events)
    
    # Calculate total hours worked at site
    total_hours = 0.0
    worker_days = {}  # Track worker activity by day
    
    for event in all_events:
        date = event.event_timestamp.date()
        if event.worker_id not in worker_days:
            worker_days[event.worker_id] = {}
        
        if date not in worker_days[event.worker_id]:
            worker_days[event.worker_id][date] = {"ins": [], "outs": []}
        
        if event.event_type == "IN":
            worker_days[event.worker_id][date]["ins"].append(event)
        else:
            worker_days[event.worker_id][date]["outs"].append(event)
    
    # Calculate hours
    for worker_id, dates in worker_days.items():
        for date, day_events in dates.items():
            if day_events["ins"] and day_events["outs"]:
                first_in = min(day_events["ins"], key=lambda x: x.event_timestamp)
                last_out = max(day_events["outs"], key=lambda x: x.event_timestamp)
                hours = (last_out.event_timestamp - first_in.event_timestamp).total_seconds() / 3600
                total_hours += hours
    
    # Find busiest day
    daily_activity = {}
    for event in all_events:
        date = event.event_timestamp.date()
        daily_activity[date] = daily_activity.get(date, 0) + 1
    
    busiest_day = None
    if daily_activity:
        busiest_date = max(daily_activity.items(), key=lambda x: x[1])
        busiest_day = {
            "date": busiest_date[0].strftime("%Y-%m-%d"),
            "event_count": busiest_date[1]
        }
    
    # Build event responses
    event_responses = []
    for event in events:
        worker = db.query(Worker).filter(Worker.id == event.worker_id).first()
        
        checkpoint_name = None
        if event.checkpoint_id:
            from app.models.checkpoint import Checkpoint
            checkpoint = db.query(Checkpoint).filter(Checkpoint.id == event.checkpoint_id).first()
            if checkpoint:
                checkpoint_name = checkpoint.name
        
        event_responses.append(TimelineEventResponse(
            id=event.id,
            worker_id=event.worker_id,
            worker_name=worker.name if worker else "Unknown",
            site_id=event.site_id,
            site_name=site.name,
            event_type=event.event_type,
            event_timestamp=event.event_timestamp,
            gps_lat=event.gps_lat,
            gps_lon=event.gps_lon,
            accuracy_m=event.accuracy_m,
            distance_m=event.distance_m,
            is_valid=event.is_valid,
            checkpoint_id=event.checkpoint_id,
            checkpoint_name=checkpoint_name
        ))
    
    return SiteActivityResponse(
        site_id=site.id,
        site_name=site.name,
        period={
            "start_date": start_dt.strftime("%Y-%m-%d") if start_date else (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d") if end_date else datetime.utcnow().strftime("%Y-%m-%d")
        },
        total_events=len(all_events),
        unique_workers=len(unique_workers),
        total_hours_worked=round(total_hours, 2),
        busiest_day=busiest_day,
        events=event_responses
    )


@router.get("/daily/{date}")
async def get_daily_timeline(
    date: str,
    site_id: Optional[int] = Query(None, description="Filter by specific site"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chronological timeline of all events for a specific day.
    
    Shows check-ins and check-outs in order, like a security log.
    """
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        next_date = target_date + timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Build query
    query = db.query(ClockEvent).filter(
        and_(
            ClockEvent.event_timestamp >= target_date,
            ClockEvent.event_timestamp < next_date
        )
    )
    
    # Apply site filter with permissions
    if site_id:
        if not can_access_site(current_user, site_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this site's timeline"
            )
        query = query.filter(ClockEvent.site_id == site_id)
    else:
        # Apply organization filter
        if current_user.organization_id != 1:
            if current_user.role == "admin":
                site_ids = db.query(Site.id).filter(
                    Site.organization_id == current_user.organization_id
                ).all()
                site_ids = [s[0] for s in site_ids]
                query = query.filter(ClockEvent.site_id.in_(site_ids))
            
            elif current_user.role == "manager":
                from app.models.user import user_sites
                site_ids = db.query(user_sites.c.site_id).filter(
                    user_sites.c.user_id == current_user.id
                ).all()
                site_ids = [s[0] for s in site_ids]
                query = query.filter(ClockEvent.site_id.in_(site_ids))
    
    # Get events in chronological order
    events = query.order_by(ClockEvent.event_timestamp.asc()).all()
    
    # Build responses
    timeline = []
    for event in events:
        worker = db.query(Worker).filter(Worker.id == event.worker_id).first()
        site = db.query(Site).filter(Site.id == event.site_id).first()
        
        checkpoint_name = None
        if event.checkpoint_id:
            from app.models.checkpoint import Checkpoint
            checkpoint = db.query(Checkpoint).filter(Checkpoint.id == event.checkpoint_id).first()
            if checkpoint:
                checkpoint_name = checkpoint.name
        
        timeline.append(TimelineEventResponse(
            id=event.id,
            worker_id=event.worker_id,
            worker_name=worker.name if worker else "Unknown",
            site_id=event.site_id,
            site_name=site.name if site else "Unknown",
            event_type=event.event_type,
            event_timestamp=event.event_timestamp,
            gps_lat=event.gps_lat,
            gps_lon=event.gps_lon,
            accuracy_m=event.accuracy_m,
            distance_m=event.distance_m,
            is_valid=event.is_valid,
            checkpoint_id=event.checkpoint_id,
            checkpoint_name=checkpoint_name
        ))
    
    return {
        "date": date,
        "total_events": len(timeline),
        "timeline": timeline
    }