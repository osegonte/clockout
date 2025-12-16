from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.worker import Worker

router = APIRouter()


# Pydantic schemas
class WorkerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    organization_id: int
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
async def create_worker(worker: WorkerCreate, db: Session = Depends(get_db)):
    """Create a new worker"""
    db_worker = Worker(**worker.model_dump())
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    return db_worker


@router.get("/", response_model=List[WorkerResponse])
async def list_workers(
    organization_id: Optional[int] = None,
    site_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all workers, optionally filtered by organization or site"""
    query = db.query(Worker)
    if organization_id:
        query = query.filter(Worker.organization_id == organization_id)
    if site_id:
        query = query.filter(Worker.site_id == site_id)
    return query.all()


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(worker_id: int, db: Session = Depends(get_db)):
    """Get a specific worker by ID"""
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    worker_update: WorkerCreate,
    db: Session = Depends(get_db)
):
    """Update a worker's details"""
    db_worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not db_worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    for key, value in worker_update.model_dump().items():
        setattr(db_worker, key, value)
    
    db.commit()
    db.refresh(db_worker)
    return db_worker


@router.delete("/{worker_id}", status_code=204)
async def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    """Delete a worker (or mark as inactive)"""
    db_worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not db_worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Better practice: mark as inactive instead of deleting
    db_worker.is_active = False
    db.commit()
    return None