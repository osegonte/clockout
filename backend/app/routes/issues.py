from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.worker import Worker
from app.models.task import IssueReport
from app.models.site import Site
from app.schemas.task import (
    IssueReportCreate, IssueReportUpdate, IssueReportResponse
)
from app.routes.worker_auth import get_current_user, get_current_worker

router = APIRouter(prefix="/issues", tags=["Issue Reports"])


# ==========================================
# WORKER ENDPOINTS
# ==========================================

@router.post("", response_model=IssueReportResponse, status_code=status.HTTP_201_CREATED)
async def create_issue_report(
    issue_data: IssueReportCreate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Worker reports an issue (pest, disease, equipment, etc.)
    """
    # Verify site belongs to organization
    site = db.query(Site).filter(
        Site.id == issue_data.site_id,
        Site.organization_id == current_worker.organization_id
    ).first()
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Create issue report
    new_issue = IssueReport(
        **issue_data.model_dump(),
        reporter_id=current_worker.id,
        organization_id=current_worker.organization_id,
        status="open"
    )
    
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)
    
    # TODO: Send notification to managers
    
    return enrich_issue_response(new_issue, db)


@router.get("/my/reports", response_model=List[IssueReportResponse])
async def get_my_issue_reports(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get issue reports created by current worker.
    """
    query = db.query(IssueReport).filter(
        IssueReport.reporter_id == current_worker.id
    )
    
    if status:
        query = query.filter(IssueReport.status == status)
    
    query = query.order_by(IssueReport.created_at.desc())
    
    issues = query.limit(limit).all()
    
    return [enrich_issue_response(issue, db) for issue in issues]


@router.get("/{issue_id}", response_model=IssueReportResponse)
async def get_issue_report(
    issue_id: int,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Get specific issue report details.
    """
    issue = db.query(IssueReport).filter(
        IssueReport.id == issue_id,
        IssueReport.reporter_id == current_worker.id
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue report not found"
        )
    
    return enrich_issue_response(issue, db)


# ==========================================
# MANAGER/ADMIN ENDPOINTS
# ==========================================

@router.get("/all", response_model=List[IssueReportResponse])
async def list_all_issues(
    site_id: Optional[int] = None,
    issue_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Managers/Admins view all issue reports in their organization.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can view all issues"
        )
    
    query = db.query(IssueReport).filter(
        IssueReport.organization_id == current_user.organization_id
    )
    
    # Apply filters
    if site_id:
        query = query.filter(IssueReport.site_id == site_id)
    
    if issue_type:
        query = query.filter(IssueReport.issue_type == issue_type)
    
    if severity:
        query = query.filter(IssueReport.severity == severity)
    
    if status:
        query = query.filter(IssueReport.status == status)
    
    # Order by severity and date
    severity_order = {
        'severe': 1,
        'moderate': 2,
        'minor': 3
    }
    
    query = query.order_by(
        IssueReport.status.asc(),  # Open issues first
        IssueReport.created_at.desc()
    )
    
    issues = query.offset(skip).limit(limit).all()
    
    return [enrich_issue_response(issue, db) for issue in issues]


@router.put("/{issue_id}", response_model=IssueReportResponse)
async def update_issue_report(
    issue_id: int,
    issue_update: IssueReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manager/Admin updates issue status and adds resolution notes.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update issues"
        )
    
    issue = db.query(IssueReport).filter(
        IssueReport.id == issue_id,
        IssueReport.organization_id == current_user.organization_id
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue report not found"
        )
    
    # Update fields
    update_data = issue_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(issue, field, value)
    
    # Set resolved_at if status changed to resolved/closed
    if issue_update.status in ['resolved', 'closed'] and not issue.resolved_at:
        issue.resolved_at = datetime.utcnow()
    
    issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)
    
    # TODO: Send notification to reporter
    
    return enrich_issue_response(issue, db)


@router.post("/{issue_id}/assign", response_model=IssueReportResponse)
async def assign_issue(
    issue_id: int,
    assigned_to_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign issue to a manager for investigation.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can assign issues"
        )
    
    issue = db.query(IssueReport).filter(
        IssueReport.id == issue_id,
        IssueReport.organization_id == current_user.organization_id
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue report not found"
        )
    
    # Verify assigned user exists and is a manager
    assigned_user = db.query(User).filter(
        User.id == assigned_to_user_id,
        User.organization_id == current_user.organization_id,
        User.role.in_(["admin", "manager"])
    ).first()
    
    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not a manager"
        )
    
    issue.assigned_to = assigned_to_user_id
    issue.status = "investigating"
    issue.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(issue)
    
    # TODO: Send notification to assigned user
    
    return enrich_issue_response(issue, db)


@router.get("/stats/summary", response_model=dict)
async def get_issue_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get issue statistics for dashboard.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can view stats"
        )
    
    # Count by status
    open_count = db.query(IssueReport).filter(
        IssueReport.organization_id == current_user.organization_id,
        IssueReport.status == 'open'
    ).count()
    
    investigating_count = db.query(IssueReport).filter(
        IssueReport.organization_id == current_user.organization_id,
        IssueReport.status == 'investigating'
    ).count()
    
    resolved_count = db.query(IssueReport).filter(
        IssueReport.organization_id == current_user.organization_id,
        IssueReport.status == 'resolved'
    ).count()
    
    # Count by severity (open only)
    severe_count = db.query(IssueReport).filter(
        IssueReport.organization_id == current_user.organization_id,
        IssueReport.status.in_(['open', 'investigating']),
        IssueReport.severity == 'severe'
    ).count()
    
    # Count by type (open only)
    type_counts = db.query(
        IssueReport.issue_type,
        func.count(IssueReport.id)
    ).filter(
        IssueReport.organization_id == current_user.organization_id,
        IssueReport.status.in_(['open', 'investigating'])
    ).group_by(IssueReport.issue_type).all()
    
    return {
        "open": open_count,
        "investigating": investigating_count,
        "resolved": resolved_count,
        "severe_active": severe_count,
        "by_type": {type_name: count for type_name, count in type_counts}
    }


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def enrich_issue_response(issue: IssueReport, db: Session) -> IssueReportResponse:
    """Add computed fields to issue response"""
    reporter = db.query(Worker).filter(Worker.id == issue.reporter_id).first()
    site = db.query(Site).filter(Site.id == issue.site_id).first()
    
    issue_dict = IssueReportResponse.model_validate(issue).model_dump()
    issue_dict['reporter_name'] = reporter.name if reporter else None
    issue_dict['site_name'] = site.name if site else None
    
    return IssueReportResponse(**issue_dict)