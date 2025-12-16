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

router = APIRouter()


# Pydantic schemas
class ClockEventCreate(BaseModel):
    worker_id: int
    site_id: int
    device_id: str  # Device unique identifier
    event_type: str  # IN or OUT
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
    """Calculate distance between two GPS coordinates in meters (Haversine formula)"""
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def validate_geofence(event: ClockEventCreate, site: Site) -> tuple[bool, float]:
    """Check if event is within site geofence"""
    distance = calculate_distance(
        event.gps_lat, event.gps_lon,
        site.gps_lat, site.gps_lon
    )
    is_valid = distance <= site.radius_m
    return is_valid, distance


@router.post("/", response_model=ClockEventResponse, status_code=201)
async def create_event(event: ClockEventCreate, db: Session = Depends(get_db)):
    """Submit a single clock-in/out event"""
    
    # Get or create device
    device = db.query(Device).filter(Device.device_id == event.device_id).first()
    if not device:
        device = Device(device_id=event.device_id, organization_id=1)  # Default org
        db.add(device)
        db.commit()
        db.refresh(device)
    
    # Get site for geofence validation
    site = db.query(Site).filter(Site.id == event.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
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
async def create_events_bulk(events: List[ClockEventCreate], db: Session = Depends(get_db)):
    """Bulk upload events - for offline sync"""
    created_events = []
    
    for event in events:
        # Check for duplicate (same worker, site, timestamp)
        existing = db.query(ClockEvent).filter(
            and_(
                ClockEvent.worker_id == event.worker_id,
                ClockEvent.site_id == event.site_id,
                ClockEvent.event_timestamp == event.event_timestamp
            )
        ).first()
        
        if existing:
            # Skip duplicate (server wins conflict resolution)
            continue
        
        # Get or create device
        device = db.query(Device).filter(Device.device_id == event.device_id).first()
        if not device:
            device = Device(device_id=event.device_id, organization_id=1)
            db.add(device)
            db.commit()
            db.refresh(device)
        
        # Get site
        site = db.query(Site).filter(Site.id == event.site_id).first()
        if not site:
            continue  # Skip if site doesn't exist
        
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
    
    # Refresh all
    for event in created_events:
        db.refresh(event)
    
    return created_events


@router.get("/", response_model=List[ClockEventResponse])
async def list_events(
    site_id: Optional[int] = None,
    worker_id: Optional[int] = None,
    date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """List events with optional filters"""
    query = db.query(ClockEvent)
    
    if site_id:
        query = query.filter(ClockEvent.site_id == site_id)
    if worker_id:
        query = query.filter(ClockEvent.worker_id == worker_id)
    if date:
        query = query.filter(func.date(ClockEvent.event_timestamp) == date)
    
    return query.order_by(ClockEvent.event_timestamp.desc()).all()