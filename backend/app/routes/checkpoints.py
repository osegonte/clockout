"""
Stage 2.5: Checkpoints API
Preparing for NFC implementation in Stage 6
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.checkpoint import Checkpoint
from app.models.site import Site
from app.models.user import User
from app.auth import get_current_user


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class CheckpointBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    checkpoint_type: str = Field(..., description="Type: entrance, exit, patrol, other")
    gps_lat: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon: Optional[float] = Field(None, ge=-180, le=180)
    nfc_tag_id: Optional[str] = Field(None, max_length=100, description="NFC tag identifier (for Stage 6)")
    qr_code: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class CheckpointCreate(CheckpointBase):
    site_id: int


class CheckpointUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    checkpoint_type: Optional[str] = None
    gps_lat: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon: Optional[float] = Field(None, ge=-180, le=180)
    nfc_tag_id: Optional[str] = Field(None, max_length=100)
    qr_code: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class CheckpointResponse(CheckpointBase):
    id: int
    site_id: int
    site_name: str
    created_at: datetime
    updated_at: Optional[datetime]
    last_used: Optional[datetime]
    total_scans: int

    class Config:
        from_attributes = True


class CheckpointListResponse(BaseModel):
    checkpoints: List[CheckpointResponse]
    total_count: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def can_access_site(user: User, site_id: int, db: Session) -> bool:
    """Check if user can access this site"""
    # Super admin (org_id=1) can access everything
    if user.organization_id == 1:
        return True
    
    # Check if site belongs to user's organization
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return False
    
    if site.organization_id != user.organization_id:
        return False
    
    # Admins can access all sites in their org
    if user.role == "admin":
        return True
    
    # Managers need to be assigned to the site
    if user.role == "manager":
        from app.models.user import user_sites
        assigned = db.query(user_sites).filter(
            user_sites.c.user_id == user.id,
            user_sites.c.site_id == site_id
        ).first()
        return assigned is not None
    
    return False


def get_checkpoint_stats(checkpoint_id: int, db: Session) -> dict:
    """Get checkpoint usage statistics"""
    from app.models.event import ClockEvent
    
    # Count scans
    total_scans = db.query(ClockEvent).filter(
        ClockEvent.checkpoint_id == checkpoint_id
    ).count()
    
    # Get last used
    last_event = db.query(ClockEvent).filter(
        ClockEvent.checkpoint_id == checkpoint_id
    ).order_by(ClockEvent.event_timestamp.desc()).first()
    
    last_used = last_event.event_timestamp if last_event else None
    
    return {
        "total_scans": total_scans,
        "last_used": last_used
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    checkpoint: CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new checkpoint at a site.
    
    - **Managers/Admins** can create checkpoints at sites they manage
    - **Super Admin** can create checkpoints anywhere
    
    Prepares for NFC implementation in Stage 6.
    """
    # Check access
    if not can_access_site(current_user, checkpoint.site_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create checkpoints at this site"
        )
    
    # Validate site exists
    site = db.query(Site).filter(Site.id == checkpoint.site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Validate checkpoint type
    valid_types = ["entrance", "exit", "patrol", "other"]
    if checkpoint.checkpoint_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid checkpoint_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Check for duplicate NFC tag
    if checkpoint.nfc_tag_id:
        existing = db.query(Checkpoint).filter(
            Checkpoint.nfc_tag_id == checkpoint.nfc_tag_id,
            Checkpoint.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NFC tag ID already in use"
            )
    
    # Create checkpoint
    new_checkpoint = Checkpoint(
        site_id=checkpoint.site_id,
        name=checkpoint.name,
        description=checkpoint.description,
        checkpoint_type=checkpoint.checkpoint_type,
        gps_lat=checkpoint.gps_lat,
        gps_lon=checkpoint.gps_lon,
        nfc_tag_id=checkpoint.nfc_tag_id,
        qr_code=checkpoint.qr_code,
        is_active=checkpoint.is_active
    )
    
    db.add(new_checkpoint)
    db.commit()
    db.refresh(new_checkpoint)
    
    # Get stats
    stats = get_checkpoint_stats(new_checkpoint.id, db)
    
    return CheckpointResponse(
        id=new_checkpoint.id,
        site_id=new_checkpoint.site_id,
        site_name=site.name,
        name=new_checkpoint.name,
        description=new_checkpoint.description,
        checkpoint_type=new_checkpoint.checkpoint_type,
        gps_lat=new_checkpoint.gps_lat,
        gps_lon=new_checkpoint.gps_lon,
        nfc_tag_id=new_checkpoint.nfc_tag_id,
        qr_code=new_checkpoint.qr_code,
        is_active=new_checkpoint.is_active,
        created_at=new_checkpoint.created_at,
        updated_at=new_checkpoint.updated_at,
        last_used=stats["last_used"],
        total_scans=stats["total_scans"]
    )


@router.get("/", response_model=CheckpointListResponse)
async def list_checkpoints(
    site_id: Optional[int] = None,
    checkpoint_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all checkpoints accessible to the current user.
    
    - **Managers** see checkpoints at assigned sites
    - **Admins** see all checkpoints in their organization
    - **Super Admin** sees all checkpoints
    
    Optional filters:
    - site_id: Filter by specific site
    - checkpoint_type: entrance, exit, patrol, other
    - is_active: true/false
    """
    query = db.query(Checkpoint).filter(Checkpoint.deleted_at.is_(None))
    
    # Apply permissions
    if current_user.organization_id != 1:  # Not super admin
        if current_user.role == "admin":
            # Admin sees all sites in their org
            site_ids = db.query(Site.id).filter(
                Site.organization_id == current_user.organization_id
            ).all()
            site_ids = [s[0] for s in site_ids]
            query = query.filter(Checkpoint.site_id.in_(site_ids))
        
        elif current_user.role == "manager":
            # Manager sees only assigned sites
            from app.models.user import user_sites
            site_ids = db.query(user_sites.c.site_id).filter(
                user_sites.c.user_id == current_user.id
            ).all()
            site_ids = [s[0] for s in site_ids]
            query = query.filter(Checkpoint.site_id.in_(site_ids))
    
    # Apply filters
    if site_id:
        # Check access
        if not can_access_site(current_user, site_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this site's checkpoints"
            )
        query = query.filter(Checkpoint.site_id == site_id)
    
    if checkpoint_type:
        query = query.filter(Checkpoint.checkpoint_type == checkpoint_type)
    
    if is_active is not None:
        query = query.filter(Checkpoint.is_active == is_active)
    
    # Execute
    checkpoints = query.all()
    
    # Build responses
    results = []
    for cp in checkpoints:
        site = db.query(Site).filter(Site.id == cp.site_id).first()
        stats = get_checkpoint_stats(cp.id, db)
        
        results.append(CheckpointResponse(
            id=cp.id,
            site_id=cp.site_id,
            site_name=site.name if site else "Unknown",
            name=cp.name,
            description=cp.description,
            checkpoint_type=cp.checkpoint_type,
            gps_lat=cp.gps_lat,
            gps_lon=cp.gps_lon,
            nfc_tag_id=cp.nfc_tag_id,
            qr_code=cp.qr_code,
            is_active=cp.is_active,
            created_at=cp.created_at,
            updated_at=cp.updated_at,
            last_used=stats["last_used"],
            total_scans=stats["total_scans"]
        ))
    
    return CheckpointListResponse(
        checkpoints=results,
        total_count=len(results)
    )


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific checkpoint"""
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.deleted_at.is_(None)
    ).first()
    
    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found"
        )
    
    # Check access
    if not can_access_site(current_user, checkpoint.site_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this checkpoint"
        )
    
    site = db.query(Site).filter(Site.id == checkpoint.site_id).first()
    stats = get_checkpoint_stats(checkpoint.id, db)
    
    return CheckpointResponse(
        id=checkpoint.id,
        site_id=checkpoint.site_id,
        site_name=site.name if site else "Unknown",
        name=checkpoint.name,
        description=checkpoint.description,
        checkpoint_type=checkpoint.checkpoint_type,
        gps_lat=checkpoint.gps_lat,
        gps_lon=checkpoint.gps_lon,
        nfc_tag_id=checkpoint.nfc_tag_id,
        qr_code=checkpoint.qr_code,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at,
        updated_at=checkpoint.updated_at,
        last_used=stats["last_used"],
        total_scans=stats["total_scans"]
    )


@router.put("/{checkpoint_id}", response_model=CheckpointResponse)
async def update_checkpoint(
    checkpoint_id: int,
    update_data: CheckpointUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update checkpoint details.
    
    Used to:
    - Update checkpoint location/name
    - Associate NFC tags (Stage 6)
    - Activate/deactivate checkpoints
    """
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.deleted_at.is_(None)
    ).first()
    
    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found"
        )
    
    # Check access
    if not can_access_site(current_user, checkpoint.site_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this checkpoint"
        )
    
    # Validate checkpoint type if provided
    if update_data.checkpoint_type:
        valid_types = ["entrance", "exit", "patrol", "other"]
        if update_data.checkpoint_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid checkpoint_type. Must be one of: {', '.join(valid_types)}"
            )
    
    # Check for duplicate NFC tag if updating
    if update_data.nfc_tag_id and update_data.nfc_tag_id != checkpoint.nfc_tag_id:
        existing = db.query(Checkpoint).filter(
            Checkpoint.nfc_tag_id == update_data.nfc_tag_id,
            Checkpoint.id != checkpoint_id,
            Checkpoint.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NFC tag ID already in use"
            )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(checkpoint, field, value)
    
    checkpoint.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(checkpoint)
    
    site = db.query(Site).filter(Site.id == checkpoint.site_id).first()
    stats = get_checkpoint_stats(checkpoint.id, db)
    
    return CheckpointResponse(
        id=checkpoint.id,
        site_id=checkpoint.site_id,
        site_name=site.name if site else "Unknown",
        name=checkpoint.name,
        description=checkpoint.description,
        checkpoint_type=checkpoint.checkpoint_type,
        gps_lat=checkpoint.gps_lat,
        gps_lon=checkpoint.gps_lon,
        nfc_tag_id=checkpoint.nfc_tag_id,
        qr_code=checkpoint.qr_code,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at,
        updated_at=checkpoint.updated_at,
        last_used=stats["last_used"],
        total_scans=stats["total_scans"]
    )


@router.delete("/{checkpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-delete a checkpoint.
    
    Only admins and super admin can delete checkpoints.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete checkpoints"
        )
    
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.deleted_at.is_(None)
    ).first()
    
    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found"
        )
    
    # Check access
    if not can_access_site(current_user, checkpoint.site_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this checkpoint"
        )
    
    # Soft delete
    checkpoint.deleted_at = datetime.utcnow()
    db.commit()
    
    return None