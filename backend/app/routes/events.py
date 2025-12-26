from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from datetime import datetime, date
import math

from app.database import get_db
from app.models.event import ClockEvent, Device
from app.models.site import Site
from app.models.worker import Worker
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()


class ClockEventCreate(BaseModel):
    worker_id: int
    site_id: int
    device_id: str
    event_type: str
    event_timestamp: datetime
    gps_lat: float
    gps_lon: float
    accuracy_m: Optional[float] = None


class ClockEventResponse(BaseModel):
    id: int
    worker_id: int
    site_id: int
    event_type: str
    event_timestamp: datetime
    gps_lat: float
    gps_lon: float
    is_valid: bool
    distance_m: Optional[float]
    
    class Config:
        from_attributes = True


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def validate_geofence(event: ClockEventCreate, site: Site) -> tuple[bool, float]:
    distance = calculate_distance(event.gps_lat, event.gps_lon, site.gps_lat, site.gps_lon)
    is_valid = distance <= site.radius_m
    return is_valid, distance


@router.post("/", response_model=ClockEventResponse, status_code=201)
async def create_event(
    event: ClockEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a clock event (check-in or check-out)
    
    FIXED: Validates site and worker belong to user's organization
    """
    # Validate site exists and belongs to user's organization
    site = db.query(Site).filter(
        Site.id == event.site_id,
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    ).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found or access denied")
    
    # Validate worker exists and belongs to user's organization
    worker = db.query(Worker).filter(
        Worker.id == event.worker_id,
        Worker.organization_id == current_user.organization_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found or access denied")
    
    # Get or create device
    device = db.query(Device).filter(
        Device.device_id == event.device_id,
        Device.organization_id == current_user.organization_id
    ).first()
    
    if not device:
        device = Device(
            device_id=event.device_id,
            organization_id=current_user.organization_id,
            site_id=event.site_id
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    
    # Validate geofence
    is_valid, distance = validate_geofence(event, site)
    
    # Create event
    db_event = ClockEvent(
        worker_id=event.worker_id,
        site_id=event.site_id,
        device_id=device.id,
        event_type=event.event_type,
        event_timestamp=event.event_timestamp,
        gps_lat=event.gps_lat,
        gps_lon=event.gps_lon,
        accuracy_m=event.accuracy_m,
        is_valid=is_valid,
        distance_m=distance
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Update device last sync
    device.last_sync = datetime.utcnow()
    db.commit()
    
    return db_event


@router.post("/bulk", response_model=List[ClockEventResponse])
async def create_events_bulk(
    events: List[ClockEventCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk create clock events (for offline sync)
    
    FIXED: Validates all events belong to user's organization
    """
    created_events = []
    
    for event in events:
        # Check for duplicates
        existing = db.query(ClockEvent).filter(
            and_(
                ClockEvent.worker_id == event.worker_id,
                ClockEvent.site_id == event.site_id,
                ClockEvent.event_timestamp == event.event_timestamp
            )
        ).first()
        
        if existing:
            continue
        
        # Validate site belongs to user's organization
        site = db.query(Site).filter(
            Site.id == event.site_id,
            Site.organization_id == current_user.organization_id,
            Site.deleted_at.is_(None)
        ).first()
        
        if not site:
            continue  # Skip events for inaccessible sites
        
        # Validate worker belongs to user's organization
        worker = db.query(Worker).filter(
            Worker.id == event.worker_id,
            Worker.organization_id == current_user.organization_id,
            Worker.deleted_at.is_(None)
        ).first()
        
        if not worker:
            continue  # Skip events for inaccessible workers
        
        # Get or create device
        device = db.query(Device).filter(
            Device.device_id == event.device_id,
            Device.organization_id == current_user.organization_id
        ).first()
        
        if not device:
            device = Device(
                device_id=event.device_id,
                organization_id=current_user.organization_id,
                site_id=event.site_id
            )
            db.add(device)
            db.commit()
            db.refresh(device)
        
        # Validate geofence
        is_valid, distance = validate_geofence(event, site)
        
        # Create event
        db_event = ClockEvent(
            worker_id=event.worker_id,
            site_id=event.site_id,
            device_id=device.id,
            event_type=event.event_type,
            event_timestamp=event.event_timestamp,
            gps_lat=event.gps_lat,
            gps_lon=event.gps_lon,
            accuracy_m=event.accuracy_m,
            is_valid=is_valid,
            distance_m=distance
        )
        
        db.add(db_event)
        created_events.append(db_event)
    
    db.commit()
    
    for event in created_events:
        db.refresh(event)
    
    return created_events


@router.get("/", response_model=List[ClockEventResponse])
async def list_events(
    site_id: Optional[int] = None,
    worker_id: Optional[int] = None,
    date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List clock events in current user's organization
    
    FIXED: Now properly filters by organization_id
    """
    # Get all sites in user's organization
    site_ids = db.query(Site.id).filter(
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    ).all()
    site_ids = [s[0] for s in site_ids]
    
    if not site_ids:
        return []
    
    # Build query filtering by organization's sites
    query = db.query(ClockEvent).filter(ClockEvent.site_id.in_(site_ids))
    
    # Apply additional filters
    if site_id:
        # Verify site belongs to user's organization
        if site_id not in site_ids:
            raise HTTPException(status_code=403, detail="Access denied to this site")
        query = query.filter(ClockEvent.site_id == site_id)
    
    if worker_id:
        # Verify worker belongs to user's organization
        worker = db.query(Worker).filter(
            Worker.id == worker_id,
            Worker.organization_id == current_user.organization_id
        ).first()
        if not worker:
            raise HTTPException(status_code=403, detail="Access denied to this worker")
        query = query.filter(ClockEvent.worker_id == worker_id)
    
    if date:
        query = query.filter(func.date(ClockEvent.event_timestamp) == date)
    
    return query.order_by(ClockEvent.event_timestamp.desc()).all()