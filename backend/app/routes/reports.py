from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date, time
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from pydantic import BaseModel
import csv
import io

from app.database import get_db
from app.models.user import User, Organization
from app.models.worker import Worker
from app.models.site import Site
from app.models.event import ClockEvent
from app.routes.auth import get_current_user

router = APIRouter()

# ==========================================
# TIMEZONE HANDLING (WAT = UTC+1)
# ==========================================
WAT_OFFSET = timedelta(hours=1)

def to_wat(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to West Africa Time (WAT)"""
    if utc_dt:
        return utc_dt + WAT_OFFSET
    return None

def get_wat_now() -> datetime:
    """Get current time in WAT"""
    return datetime.utcnow() + WAT_OFFSET


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class WorkerAttendanceStatus(BaseModel):
    worker_id: int
    name: str
    check_in_time: Optional[str]
    check_out_time: Optional[str]
    hours_worked: Optional[float]  # FIXED: Changed from Optional<float> to Optional[float]
    status: str  # on_time, late, absent, present
    
    class Config:
        from_attributes = True


class DailySummaryResponse(BaseModel):
    date: str
    site_name: Optional[str]
    total_workers: int
    present: int
    absent: int
    late: int
    on_time: int
    total_hours_worked: float
    workers_present: List[WorkerAttendanceStatus]
    workers_absent: List[Dict[str, Any]]


class WorkerOnSite(BaseModel):
    worker_id: int
    name: str
    site_name: str
    checked_in_at: str
    hours_on_site: float


class WorkerStatusResponse(BaseModel):
    timestamp: str
    on_site_now: List[WorkerOnSite]
    checked_out: List[Dict[str, Any]]
    not_yet_arrived: List[Dict[str, Any]]


class LateArrival(BaseModel):
    date: str
    worker_id: int
    worker_name: str
    site_name: str
    expected_time: str
    actual_time: str
    minutes_late: int


class LateArrivalsResponse(BaseModel):
    period: Dict[str, str]
    total_late_arrivals: int
    late_arrivals: List[LateArrival]
    top_offenders: List[Dict[str, Any]]


class AnalyticsOverview(BaseModel):
    period_days: int
    platform_stats: Dict[str, int]
    attendance_trend: List[Dict[str, Any]]
    organizations_by_plan: Dict[str, int]
    top_sites_by_activity: List[Dict[str, Any]]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_accessible_sites(current_user: User, db: Session, site_id: Optional[int] = None) -> List[int]:
    """
    Get list of site IDs the user can access
    - Managers: Only their assigned sites
    - Admins: All sites in their organization
    """
    if current_user.user_mode == "admin" or current_user.role == "admin":
        # Admin sees all sites in their org
        sites = db.query(Site.id).filter(
            Site.organization_id == current_user.organization_id,
            Site.deleted_at.is_(None)
        ).all()
        site_ids = [s[0] for s in sites]
    else:
        # Manager sees only assigned sites
        result = db.execute(
            text("SELECT site_id FROM user_sites WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        )
        site_ids = [row[0] for row in result]
    
    # If specific site requested, verify access
    if site_id:
        if site_id not in site_ids:
            raise HTTPException(status_code=403, detail="Access denied to this site")
        return [site_id]
    
    return site_ids


def is_late(check_in_time: datetime, site: Site) -> tuple[bool, int]:
    """
    Check if check-in is late
    Returns: (is_late, minutes_late)
    """
    expected_time = site.checkin_start if site.checkin_start else time(6, 0, 0)
    
    # Convert check_in_time to WAT
    check_in_wat = to_wat(check_in_time)
    check_in_time_only = check_in_wat.time()
    
    # Compare times
    if check_in_time_only > expected_time:
        # Calculate minutes late
        expected_dt = datetime.combine(check_in_wat.date(), expected_time)
        actual_dt = datetime.combine(check_in_wat.date(), check_in_time_only)
        minutes_late = int((actual_dt - expected_dt).total_seconds() / 60)
        return True, minutes_late
    
    return False, 0


# ==========================================
# ENDPOINT 1: DAILY SUMMARY
# ==========================================

@router.get("/daily-summary", response_model=DailySummaryResponse)
async def get_daily_summary(
    date: str,  # YYYY-MM-DD format
    organization_id: Optional[int] = None,
    site_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily attendance summary
    
    Shows who's present, absent, late, on-time for a specific date
    """
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get accessible sites
    accessible_sites = get_accessible_sites(current_user, db, site_id)
    
    if not accessible_sites:
        raise HTTPException(status_code=403, detail="No accessible sites")
    
    # Get site info
    site_name = "All Sites"
    if site_id:
        site = db.query(Site).filter(Site.id == site_id).first()
        site_name = site.name if site else "Unknown Site"
    
    # Get all workers at these sites
    all_workers = db.query(Worker).filter(
        Worker.site_id.in_(accessible_sites),
        Worker.deleted_at.is_(None),
        Worker.is_active == True
    ).all()
    
    total_workers = len(all_workers)
    
    # Get attendance events for this date
    events_query = db.query(ClockEvent).join(Site).filter(
        ClockEvent.site_id.in_(accessible_sites),
        func.date(ClockEvent.event_timestamp) == target_date
    ).order_by(ClockEvent.worker_id, ClockEvent.event_timestamp)
    
    events = events_query.all()
    
    # Group events by worker
    worker_events = {}
    for event in events:
        if event.worker_id not in worker_events:
            worker_events[event.worker_id] = []
        worker_events[event.worker_id].append(event)
    
    # Process attendance
    workers_present = []
    workers_absent = []
    late_count = 0
    on_time_count = 0
    total_hours = 0.0
    
    for worker in all_workers:
        if worker.id in worker_events:
            # Worker has events today
            worker_day_events = worker_events[worker.id]
            
            # Find check-in and check-out
            check_in_event = next((e for e in worker_day_events if e.event_type == "IN"), None)
            check_out_event = next((e for e in worker_day_events if e.event_type == "OUT"), None)
            
            if check_in_event:
                check_in_wat = to_wat(check_in_event.event_timestamp)
                check_in_time_str = check_in_wat.strftime("%H:%M:%S")
                
                # Check if late
                site = db.query(Site).filter(Site.id == check_in_event.site_id).first()
                late, minutes_late = is_late(check_in_event.event_timestamp, site)
                
                if late:
                    late_count += 1
                    status = "late"
                else:
                    on_time_count += 1
                    status = "on_time"
                
                # Calculate hours worked
                hours_worked = 0.0
                check_out_time_str = None
                
                if check_out_event:
                    check_out_wat = to_wat(check_out_event.event_timestamp)
                    check_out_time_str = check_out_wat.strftime("%H:%M:%S")
                    
                    time_diff = check_out_event.event_timestamp - check_in_event.event_timestamp
                    hours_worked = time_diff.total_seconds() / 3600
                    total_hours += hours_worked
                
                workers_present.append(WorkerAttendanceStatus(
                    worker_id=worker.id,
                    name=worker.name,
                    check_in_time=check_in_time_str,
                    check_out_time=check_out_time_str,
                    hours_worked=round(hours_worked, 2) if hours_worked > 0 else None,
                    status=status
                ))
        else:
            # Worker absent
            workers_absent.append({
                "worker_id": worker.id,
                "name": worker.name
            })
    
    return DailySummaryResponse(
        date=date,
        site_name=site_name,
        total_workers=total_workers,
        present=len(workers_present),
        absent=len(workers_absent),
        late=late_count,
        on_time=on_time_count,
        total_hours_worked=round(total_hours, 2),
        workers_present=workers_present,
        workers_absent=workers_absent
    )


# ==========================================
# ENDPOINT 2: WORKER STATUS (REAL-TIME)
# ==========================================

@router.get("/worker-status", response_model=WorkerStatusResponse)
async def get_worker_status(
    organization_id: Optional[int] = None,
    site_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time worker status
    
    Shows who's currently on-site, who's checked out, who hasn't arrived
    """
    # Get accessible sites
    accessible_sites = get_accessible_sites(current_user, db, site_id)
    
    if not accessible_sites:
        raise HTTPException(status_code=403, detail="No accessible sites")
    
    # Get today's date
    today = get_wat_now().date()
    
    # Get all workers
    all_workers = db.query(Worker).filter(
        Worker.site_id.in_(accessible_sites),
        Worker.deleted_at.is_(None),
        Worker.is_active == True
    ).all()
    
    # Get today's events
    events = db.query(ClockEvent).join(Site).filter(
        ClockEvent.site_id.in_(accessible_sites),
        func.date(ClockEvent.event_timestamp) == today
    ).order_by(ClockEvent.worker_id, ClockEvent.event_timestamp).all()
    
    # Group events by worker
    worker_events = {}
    for event in events:
        if event.worker_id not in worker_events:
            worker_events[event.worker_id] = []
        worker_events[event.worker_id].append(event)
    
    # Categorize workers
    on_site_now = []
    checked_out = []
    not_yet_arrived = []
    
    for worker in all_workers:
        if worker.id in worker_events:
            worker_day_events = worker_events[worker.id]
            
            # Check latest event
            latest_event = worker_day_events[-1]
            
            if latest_event.event_type == "IN":
                # Worker is on-site
                check_in_wat = to_wat(latest_event.event_timestamp)
                hours_on_site = (get_wat_now() - check_in_wat).total_seconds() / 3600
                
                site = db.query(Site).filter(Site.id == latest_event.site_id).first()
                
                on_site_now.append(WorkerOnSite(
                    worker_id=worker.id,
                    name=worker.name,
                    site_name=site.name if site else "Unknown",
                    checked_in_at=check_in_wat.strftime("%H:%M:%S"),
                    hours_on_site=round(hours_on_site, 2)
                ))
            else:
                # Worker checked out
                check_out_wat = to_wat(latest_event.event_timestamp)
                checked_out.append({
                    "worker_id": worker.id,
                    "name": worker.name,
                    "checked_out_at": check_out_wat.strftime("%H:%M:%S")
                })
        else:
            # Worker hasn't arrived yet
            not_yet_arrived.append({
                "worker_id": worker.id,
                "name": worker.name
            })
    
    return WorkerStatusResponse(
        timestamp=get_wat_now().isoformat(),
        on_site_now=on_site_now,
        checked_out=checked_out,
        not_yet_arrived=not_yet_arrived
    )


# ==========================================
# ENDPOINT 3: LATE ARRIVALS REPORT
# ==========================================

@router.get("/late-arrivals", response_model=LateArrivalsResponse)
async def get_late_arrivals(
    start_date: str,
    end_date: str,
    organization_id: Optional[int] = None,
    site_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get late arrivals report for a date range
    
    Shows all late check-ins and top offenders
    """
    # Parse dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    # Get accessible sites
    accessible_sites = get_accessible_sites(current_user, db, site_id)
    
    if not accessible_sites:
        raise HTTPException(status_code=403, detail="No accessible sites")
    
    # Get all check-in events in date range
    events = db.query(ClockEvent).join(Site).join(Worker).filter(
        ClockEvent.site_id.in_(accessible_sites),
        ClockEvent.event_type == "IN",
        func.date(ClockEvent.event_timestamp) >= start,
        func.date(ClockEvent.event_timestamp) <= end
    ).order_by(ClockEvent.event_timestamp.desc()).all()
    
    # Analyze late arrivals
    late_arrivals = []
    late_counts = {}  # worker_id -> count
    
    for event in events:
        site = db.query(Site).filter(Site.id == event.site_id).first()
        worker = db.query(Worker).filter(Worker.id == event.worker_id).first()
        
        late, minutes_late = is_late(event.event_timestamp, site)
        
        if late:
            event_wat = to_wat(event.event_timestamp)
            expected_time = site.checkin_start if site.checkin_start else time(6, 0, 0)
            
            late_arrivals.append(LateArrival(
                date=event_wat.strftime("%Y-%m-%d"),
                worker_id=worker.id,
                worker_name=worker.name,
                site_name=site.name,
                expected_time=expected_time.strftime("%H:%M:%S"),
                actual_time=event_wat.strftime("%H:%M:%S"),
                minutes_late=minutes_late
            ))
            
            # Count for top offenders
            if worker.id not in late_counts:
                late_counts[worker.id] = {"name": worker.name, "count": 0}
            late_counts[worker.id]["count"] += 1
    
    # Top offenders (sorted by count)
    top_offenders = [
        {"worker_id": wid, "name": data["name"], "late_count": data["count"]}
        for wid, data in sorted(late_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ][:10]  # Top 10
    
    return LateArrivalsResponse(
        period={"start_date": start_date, "end_date": end_date},
        total_late_arrivals=len(late_arrivals),
        late_arrivals=late_arrivals,
        top_offenders=top_offenders
    )


# ==========================================
# ENDPOINT 4: CSV EXPORT
# ==========================================

@router.get("/export/csv")
async def export_attendance_csv(
    start_date: str,
    end_date: str,
    organization_id: Optional[int] = None,
    site_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export attendance data as CSV
    
    Downloads a CSV file with all attendance records in date range
    """
    # Parse dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get accessible sites
    accessible_sites = get_accessible_sites(current_user, db, site_id)
    
    if not accessible_sites:
        raise HTTPException(status_code=403, detail="No accessible sites")
    
    # Get all events in date range
    events = db.query(ClockEvent).join(Site).join(Worker).filter(
        ClockEvent.site_id.in_(accessible_sites),
        func.date(ClockEvent.event_timestamp) >= start,
        func.date(ClockEvent.event_timestamp) <= end
    ).order_by(ClockEvent.event_timestamp).all()
    
    # Group by worker and date to create daily records
    daily_records = {}  # (worker_id, date) -> {check_in, check_out, ...}
    
    for event in events:
        event_wat = to_wat(event.event_timestamp)
        event_date = event_wat.date()
        key = (event.worker_id, event_date)
        
        if key not in daily_records:
            worker = db.query(Worker).filter(Worker.id == event.worker_id).first()
            site = db.query(Site).filter(Site.id == event.site_id).first()
            
            daily_records[key] = {
                "date": event_date.strftime("%Y-%m-%d"),
                "worker_id": event.worker_id,
                "worker_name": worker.name if worker else "Unknown",
                "site": site.name if site else "Unknown",
                "check_in": None,
                "check_out": None,
                "accuracy": event.accuracy_m,
                "distance_m": event.distance_m
            }
        
        if event.event_type == "IN" and not daily_records[key]["check_in"]:
            daily_records[key]["check_in"] = event_wat.strftime("%H:%M:%S")
        elif event.event_type == "OUT":
            daily_records[key]["check_out"] = event_wat.strftime("%H:%M:%S")
    
    # Calculate hours worked
    for record in daily_records.values():
        if record["check_in"] and record["check_out"]:
            check_in_dt = datetime.strptime(f"{record['date']} {record['check_in']}", "%Y-%m-%d %H:%M:%S")
            check_out_dt = datetime.strptime(f"{record['date']} {record['check_out']}", "%Y-%m-%d %H:%M:%S")
            hours = (check_out_dt - check_in_dt).total_seconds() / 3600
            record["hours_worked"] = round(hours, 2)
        else:
            record["hours_worked"] = None
        
        # Determine status
        if record["check_in"]:
            record["status"] = "Present"
        else:
            record["status"] = "Absent"
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Date", "Worker ID", "Worker Name", "Site", 
        "Check-in Time", "Check-out Time", "Hours Worked", 
        "Status", "GPS Accuracy (m)", "Distance from Site (m)"
    ])
    
    writer.writeheader()
    
    for record in sorted(daily_records.values(), key=lambda x: (x["date"], x["worker_name"])):
        writer.writerow({
            "Date": record["date"],
            "Worker ID": record["worker_id"],
            "Worker Name": record["worker_name"],
            "Site": record["site"],
            "Check-in Time": record["check_in"] or "N/A",
            "Check-out Time": record["check_out"] or "N/A",
            "Hours Worked": record["hours_worked"] if record["hours_worked"] else "N/A",
            "Status": record["status"],
            "GPS Accuracy (m)": round(record["accuracy"], 2) if record["accuracy"] else "N/A",
            "Distance from Site (m)": round(record["distance_m"], 2) if record["distance_m"] else "N/A"
        })
    
    # Return as downloadable CSV
    output.seek(0)
    filename = f"attendance_{start_date}_to_{end_date}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==========================================
# ENDPOINT 5: ANALYTICS OVERVIEW (SUPER-ADMIN)
# ==========================================

@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get platform-wide analytics overview
    
    SUPER-ADMIN ONLY: Shows stats across all organizations
    """
    # Check if super-admin (org_id=1 and admin role)
    if current_user.organization_id != 1 or (current_user.role != "admin" and current_user.user_mode != "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only super-admins can access analytics overview"
        )
    
    # Platform stats
    total_orgs = db.query(func.count(Organization.id)).filter(
        Organization.deleted_at.is_(None)
    ).scalar() or 0
    
    total_sites = db.query(func.count(Site.id)).filter(
        Site.deleted_at.is_(None)
    ).scalar() or 0
    
    total_workers = db.query(func.count(Worker.id)).filter(
        Worker.deleted_at.is_(None),
        Worker.is_active == True
    ).scalar() or 0
    
    total_managers = db.query(func.count(User.id)).filter(
        User.is_active == True,
        User.deleted_at.is_(None)
    ).filter(
        or_(User.user_mode == "manager", User.role == "manager")
    ).scalar() or 0
    
    # Calculate date range
    end_date = get_wat_now().date()
    start_date = end_date - timedelta(days=days)
    
    total_events = db.query(func.count(ClockEvent.id)).filter(
        func.date(ClockEvent.event_timestamp) >= start_date
    ).scalar() or 0
    
    # Attendance trend (daily check-ins for last N days)
    attendance_trend = []
    
    trend_query = db.execute(
        text("""
            SELECT DATE(event_timestamp) as event_date, COUNT(*) as total_check_ins
            FROM clock_events
            WHERE event_type = 'IN'
            AND DATE(event_timestamp) >= :start_date
            GROUP BY DATE(event_timestamp)
            ORDER BY event_date
        """),
        {"start_date": start_date}
    )
    
    for row in trend_query:
        attendance_trend.append({
            "date": row[0].strftime("%Y-%m-%d"),
            "total_check_ins": row[1]
        })
    
    # Organizations by plan
    org_plans = db.execute(
        text("""
            SELECT subscription_plan, COUNT(*) as count
            FROM organizations
            WHERE deleted_at IS NULL
            GROUP BY subscription_plan
        """)
    )
    
    organizations_by_plan = {}
    for row in org_plans:
        organizations_by_plan[row[0]] = row[1]
    
    # Top sites by activity
    top_sites = db.execute(
        text("""
            SELECT s.id, s.name, COUNT(ce.id) as total_events
            FROM sites s
            LEFT JOIN clock_events ce ON s.id = ce.site_id
            WHERE s.deleted_at IS NULL
            AND (ce.event_timestamp >= :start_date OR ce.event_timestamp IS NULL)
            GROUP BY s.id, s.name
            ORDER BY total_events DESC
            LIMIT 10
        """),
        {"start_date": start_date}
    )
    
    top_sites_by_activity = []
    for row in top_sites:
        top_sites_by_activity.append({
            "site_id": row[0],
            "site_name": row[1],
            "total_events": row[2]
        })
    
    return AnalyticsOverview(
        period_days=days,
        platform_stats={
            "total_organizations": total_orgs,
            "total_sites": total_sites,
            "total_workers": total_workers,
            "total_managers": total_managers,
            "total_events_recorded": total_events
        },
        attendance_trend=attendance_trend,
        organizations_by_plan=organizations_by_plan,
        top_sites_by_activity=top_sites_by_activity
    )