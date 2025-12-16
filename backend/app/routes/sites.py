from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import time

from app.database import get_db
from app.models.site import Site

router = APIRouter()


# Pydantic schemas
class SiteCreate(BaseModel):
    name: str
    organization_id: int
    gps_lat: float
    gps_lon: float
    radius_m: float = 100.0
    checkin_start: Optional[str] = None  # "06:00:00"
    checkin_end: Optional[str] = None
    checkout_start: Optional[str] = None
    checkout_end: Optional[str] = None


class SiteResponse(BaseModel):
    id: int
    name: str
    organization_id: int
    gps_lat: float
    gps_lon: float
    radius_m: float
    
    class Config:
        from_attributes = True


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(site: SiteCreate, db: Session = Depends(get_db)):
    """Create a new work site with geofence"""
    db_site = Site(**site.model_dump())
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site


@router.get("/", response_model=List[SiteResponse])
async def list_sites(
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all sites, optionally filtered by organization"""
    query = db.query(Site)
    if organization_id:
        query = query.filter(Site.organization_id == organization_id)
    return query.all()


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: int, db: Session = Depends(get_db)):
    """Get a specific site by ID"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(site_id: int, site_update: SiteCreate, db: Session = Depends(get_db)):
    """Update a site's details"""
    db_site = db.query(Site).filter(Site.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    for key, value in site_update.model_dump().items():
        setattr(db_site, key, value)
    
    db.commit()
    db.refresh(db_site)
    return db_site


@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: int, db: Session = Depends(get_db)):
    """Delete a site"""
    db_site = db.query(Site).filter(Site.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    db.delete(db_site)
    db.commit()
    return None