from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, time

from app.database import get_db
from app.models.site import Site
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class SiteCreate(BaseModel):
    name: str
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
async def create_site(
    site: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new work site with geofence in current user's organization"""
    # Automatically set organization_id from authenticated user
    db_site = Site(
        **site.model_dump(),
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site


@router.get("/", response_model=List[SiteResponse])
async def list_sites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all sites in current user's organization
    
    FIXED: Now properly filters by organization_id automatically
    """
    # CRITICAL FIX: Always filter by user's organization
    query = db.query(Site).filter(
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    )
    
    return query.all()


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific site by ID (only from user's organization)"""
    site = db.query(Site).filter(
        Site.id == site_id,
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    ).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    return site


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    site_update: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a site's details (only in user's organization)"""
    db_site = db.query(Site).filter(
        Site.id == site_id,
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    ).first()
    
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Update fields
    for key, value in site_update.model_dump(exclude_unset=True).items():
        setattr(db_site, key, value)
    
    db_site.updated_by = current_user.id
    db_site.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_site)
    return db_site


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a site"""
    db_site = db.query(Site).filter(
        Site.id == site_id,
        Site.organization_id == current_user.organization_id,
        Site.deleted_at.is_(None)
    ).first()
    
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Soft delete: set deleted_at timestamp
    db_site.deleted_at = datetime.utcnow()
    db_site.updated_by = current_user.id
    
    db.commit()
    return None