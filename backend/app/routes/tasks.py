from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models.user import User
from app.models.worker import Worker
from app.models.task import Task
from app.models.site import Site
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskStartRequest, TaskCompleteRequest,
    WorkerDashboardResponse
)
from app.routes.worker_auth import get_current_user, get_current_worker

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ==========================================
# MANAGER/ADMIN ENDPOINTS
# ==========================================

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manager/Admin creates a new task for a worker.
    """
    # Verify user has permission
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create tasks"
        )
    
    # Verify worker exists and belongs to same organization
    worker = db.query(Worker).filter(
        Worker.id == task_data.worker_id,
        Worker.organization_id == current_user.organization_id,
        Worker.is_active == True
    ).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Create task
    new_task = Task(
        **task_data.model_dump(),
        assigned_by=current_user.id,
        organization_id=current_user.organization_id,
        status="pending"
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # TODO: Send notification to worker
    
    return enrich_task_response(new_task, db)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    worker_id: Optional[int] = None,
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all tasks with optional filters.
    Managers see all tasks in their organization.
    """
    query = db.query(Task).filter(
        Task.organization_id == current_user.organization_id,
        Task.deleted_at == None
    )
    
    # Apply filters
    if worker_id:
        query = query.filter(Task.worker_id == worker_id)
    
    if site_id:
        query = query.filter(Task.site_id == site_id)
    
    if status:
        query = query.filter(Task.status == status)
    
    if priority:
        query = query.filter(Task.priority == priority)
    
    if due_date:
        query = query.filter(Task.due_date == due_date)
    
    # Order by priority (urgent first) then due date
    query = query.order_by(
        Task.priority.desc(),
        Task.due_date.asc().nullslast(),
        Task.created_at.desc()
    )
    
    tasks = query.offset(skip).limit(limit).all()
    
    return [enrich_task_response(task, db) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task details by ID.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.organization_id == current_user.organization_id,
        Task.deleted_at == None
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return enrich_task_response(task, db)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manager/Admin updates a task.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update tasks"
        )
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.organization_id == current_user.organization_id,
        Task.deleted_at == None
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return enrich_task_response(task, db)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a task.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete tasks"
        )
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.organization_id == current_user.organization_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Soft delete
    task.deleted_at = datetime.utcnow()
    task.status = "cancelled"
    db.commit()
    
    return None


# ==========================================
# WORKER ENDPOINTS
# ==========================================

@router.get("/my/tasks", response_model=List[TaskResponse])
async def get_my_tasks(
    status: Optional[str] = None,
    date_filter: Optional[str] = Query(None, regex="^(today|week|month|all)$"),
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Worker gets their assigned tasks.
    """
    query = db.query(Task).filter(
        Task.worker_id == current_worker.id,
        Task.deleted_at == None
    )
    
    # Filter by status
    if status:
        query = query.filter(Task.status == status)
    
    # Filter by date
    if date_filter == "today":
        query = query.filter(
            or_(
                Task.due_date == date.today(),
                Task.created_at >= func.current_date()
            )
        )
    elif date_filter == "week":
        query = query.filter(Task.created_at >= func.current_date() - func.cast('7 days', Interval))
    elif date_filter == "month":
        query = query.filter(Task.created_at >= func.current_date() - func.cast('30 days', Interval))
    
    # Order: urgent first, then by due date
    query = query.order_by(
        Task.priority.desc(),
        Task.status.asc(),  # pending first
        Task.due_date.asc().nullslast()
    )
    
    tasks = query.all()
    return [enrich_task_response(task, db) for task in tasks]


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Worker marks task as started.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.worker_id == current_worker.id,
        Task.deleted_at == None
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start task with status: {task.status}"
        )
    
    task.status = "in_progress"
    task.started_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return enrich_task_response(task, db)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    completion_data: TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Worker marks task as completed.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.worker_id == current_worker.id,
        Task.deleted_at == None
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task already completed"
        )
    
    # Update task
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.worker_notes = completion_data.worker_notes
    task.actual_quantity = completion_data.actual_quantity
    
    if completion_data.after_photos:
        task.after_photos = completion_data.after_photos
    
    # Calculate actual duration if task was started
    if task.started_at:
        duration = (task.completed_at - task.started_at).total_seconds() / 60
        task.actual_duration_minutes = int(duration)
    
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    # TODO: Send notification to manager
    
    return enrich_task_response(task, db)


@router.post("/{task_id}/add-note", response_model=TaskResponse)
async def add_task_note(
    task_id: int,
    note: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Worker adds a note to their task.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.worker_id == current_worker.id,
        Task.deleted_at == None
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Append to existing notes
    if task.worker_notes:
        task.worker_notes += f"\n\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{note}"
    else:
        task.worker_notes = note
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return enrich_task_response(task, db)


@router.get("/my/dashboard", response_model=WorkerDashboardResponse)
async def get_worker_dashboard(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get complete dashboard data for worker mobile app.
    """
    from app.models.task import AutoAttendance
    
    # Check if clocked in today
    today_attendance = db.query(AutoAttendance).filter(
        AutoAttendance.worker_id == current_worker.id,
        func.date(AutoAttendance.clock_in_time) == date.today(),
        AutoAttendance.clock_out_time == None
    ).first()
    
    # Calculate hours
    hours_today = calculate_hours_today(current_worker.id, db)
    hours_this_week = calculate_hours_this_week(current_worker.id, db)
    
    # Task counts
    task_stats = get_task_stats(current_worker.id, db)
    
    # Monthly stats
    monthly_stats = get_monthly_stats(current_worker.id, db)
    
    # Site info
    site = db.query(Site).filter(Site.id == current_worker.site_id).first()
    
    return WorkerDashboardResponse(
        clocked_in=today_attendance is not None,
        clock_in_time=today_attendance.clock_in_time if today_attendance else None,
        hours_today=hours_today,
        hours_this_week=hours_this_week,
        pending_tasks=task_stats['pending'],
        in_progress_tasks=task_stats['in_progress'],
        completed_tasks_today=task_stats['completed_today'],
        total_tasks_today=task_stats['total_today'],
        days_worked_this_month=monthly_stats['days_worked'],
        total_hours_this_month=monthly_stats['total_hours'],
        tasks_completed_this_month=monthly_stats['tasks_completed'],
        completion_rate=monthly_stats['completion_rate'],
        site_id=site.id if site else current_worker.site_id,
        site_name=site.name if site else "Unknown",
        site_gps_lat=site.gps_lat if site else 0,
        site_gps_lon=site.gps_lon if site else 0,
        site_radius_m=site.radius_m if site else 100
    )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def enrich_task_response(task: Task, db: Session) -> TaskResponse:
    """Add computed fields to task response"""
    worker = db.query(Worker).filter(Worker.id == task.worker_id).first()
    site = db.query(Site).filter(Site.id == task.site_id).first()
    assigner = db.query(User).filter(User.id == task.assigned_by).first()
    
    task_dict = TaskResponse.model_validate(task).model_dump()
    task_dict['worker_name'] = worker.name if worker else None
    task_dict['site_name'] = site.name if site else None
    task_dict['assigned_by_name'] = assigner.full_name if assigner else None
    
    return TaskResponse(**task_dict)


def calculate_hours_today(worker_id: int, db: Session) -> float:
    """Calculate total hours worked today"""
    from app.models.task import AutoAttendance
    
    attendance = db.query(func.sum(AutoAttendance.total_hours)).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time) == date.today()
    ).scalar()
    
    return float(attendance or 0)


def calculate_hours_this_week(worker_id: int, db: Session) -> float:
    """Calculate total hours this week"""
    from app.models.task import AutoAttendance
    from datetime import timedelta
    
    week_start = date.today() - timedelta(days=date.today().weekday())
    
    attendance = db.query(func.sum(AutoAttendance.total_hours)).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time) >= week_start
    ).scalar()
    
    return float(attendance or 0)


def get_task_stats(worker_id: int, db: Session) -> dict:
    """Get task statistics for worker"""
    today = date.today()
    
    # Count by status
    pending = db.query(Task).filter(
        Task.worker_id == worker_id,
        Task.status == 'pending',
        Task.deleted_at == None
    ).count()
    
    in_progress = db.query(Task).filter(
        Task.worker_id == worker_id,
        Task.status == 'in_progress',
        Task.deleted_at == None
    ).count()
    
    completed_today = db.query(Task).filter(
        Task.worker_id == worker_id,
        Task.status == 'completed',
        func.date(Task.completed_at) == today
    ).count()
    
    total_today = db.query(Task).filter(
        Task.worker_id == worker_id,
        or_(
            Task.due_date == today,
            func.date(Task.created_at) == today
        ),
        Task.deleted_at == None
    ).count()
    
    return {
        'pending': pending,
        'in_progress': in_progress,
        'completed_today': completed_today,
        'total_today': total_today
    }


def get_monthly_stats(worker_id: int, db: Session) -> dict:
    """Get monthly statistics for worker"""
    from app.models.task import AutoAttendance
    from datetime import timedelta
    
    month_start = date.today().replace(day=1)
    
    # Days worked
    days_worked = db.query(func.count(func.distinct(func.date(AutoAttendance.clock_in_time)))).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time) >= month_start
    ).scalar() or 0
    
    # Total hours
    total_hours = db.query(func.sum(AutoAttendance.total_hours)).filter(
        AutoAttendance.worker_id == worker_id,
        func.date(AutoAttendance.clock_in_time) >= month_start
    ).scalar() or 0
    
    # Tasks completed
    tasks_completed = db.query(Task).filter(
        Task.worker_id == worker_id,
        Task.status == 'completed',
        func.date(Task.completed_at) >= month_start
    ).count()
    
    # Total tasks assigned this month
    total_tasks = db.query(Task).filter(
        Task.worker_id == worker_id,
        func.date(Task.created_at) >= month_start,
        Task.deleted_at == None
    ).count()
    
    completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        'days_worked': days_worked,
        'total_hours': float(total_hours),
        'tasks_completed': tasks_completed,
        'completion_rate': round(completion_rate, 1)
    }