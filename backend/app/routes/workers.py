from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.worker import Worker
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class WorkerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    site_id: Optional[int] = None


class WorkerResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    employee_id: Optional[str]
    organization_id: int
    site_id: Optional[int]
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=WorkerResponse, status_code=201)
async def create_worker(
    worker: WorkerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new worker in the current user's organization"""
    # Automatically set organization_id from authenticated user
    db_worker = Worker(
        **worker.model_dump(),
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    return db_worker


@router.get("/", response_model=List[WorkerResponse])
async def list_workers(
    site_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all workers in current user's organization
    
    FIXED: Now properly filters by organization_id automatically
    """
    # CRITICAL FIX: Always filter by user's organization
    query = db.query(Worker).filter(
        Worker.organization_id == current_user.organization_id,
        Worker.deleted_at.is_(None)
    )
    
    # Optional site filter
    if site_id:
        query = query.filter(Worker.site_id == site_id)
    
    return query.all()


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific worker by ID (only from user's organization)"""
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.organization_id == current_user.organization_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return worker


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    worker_update: WorkerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a worker's details (only in user's organization)"""
    db_worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.organization_id == current_user.organization_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not db_worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Update fields
    for key, value in worker_update.model_dump(exclude_unset=True).items():
        setattr(db_worker, key, value)
    
    db_worker.updated_by = current_user.id
    db_worker.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_worker)
    return db_worker


@router.delete("/{worker_id}", status_code=204)
async def delete_worker(
    worker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a worker (mark as inactive)"""
    db_worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.organization_id == current_user.organization_id,
        Worker.deleted_at.is_(None)
    ).first()
    
    if not db_worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Soft delete: mark as inactive and set deleted_at
    db_worker.is_active = False
    db_worker.deleted_at = datetime.utcnow()
    db_worker.updated_by = current_user.id
    
    db.commit()
    return None