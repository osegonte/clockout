"""
Stage 2.5: Audit Log API
Track all system events for compliance and security
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.routes.auth import get_current_user


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_email: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total_count: int
    page: int
    page_size: int


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type (login, create, update, delete)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity (worker, site, user, etc)"),
    user_id: Optional[int] = Query(None, description="Filter by user who performed action"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query audit logs for compliance and security tracking.
    
    **Permissions:**
    - **Managers:** See logs for their assigned sites only
    - **Admins:** See all logs in their organization
    - **Super Admin:** See all logs across all organizations
    
    **Common Actions:**
    - login, logout
    - create, update, delete
    - clock_in, clock_out
    - export
    
    **Entity Types:**
    - worker, site, user, organization, checkpoint, device
    """
    # Only admins can view audit logs
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs"
        )
    
    # Build query
    query = db.query(AuditLog)
    
    # Apply organization filter (non-super admin)
    if current_user.organization_id != 1:  # Not super admin
        # Filter to only show logs from their organization
        # Get all user IDs in the organization
        from app.models.user import User as UserModel
        org_user_ids = db.query(UserModel.id).filter(
            UserModel.organization_id == current_user.organization_id
        ).all()
        org_user_ids = [uid[0] for uid in org_user_ids]
        
        query = query.filter(
            or_(
                AuditLog.user_id.in_(org_user_ids),
                AuditLog.user_id.is_(None)  # Include system actions
            )
        )
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination and ordering
    logs = query.order_by(AuditLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # Build responses with user info
    results = []
    for log in logs:
        user_email = None
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()
            if user:
                user_email = user.email
        
        results.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        ))
    
    return AuditLogListResponse(
        logs=results,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


@router.get("/recent", response_model=List[AuditLogResponse])
async def get_recent_audit_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get most recent audit logs.
    
    Quick view of latest system activity.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs"
        )
    
    query = db.query(AuditLog)
    
    # Apply organization filter
    if current_user.organization_id != 1:
        from app.models.user import User as UserModel
        org_user_ids = db.query(UserModel.id).filter(
            UserModel.organization_id == current_user.organization_id
        ).all()
        org_user_ids = [uid[0] for uid in org_user_ids]
        
        query = query.filter(
            or_(
                AuditLog.user_id.in_(org_user_ids),
                AuditLog.user_id.is_(None)
            )
        )
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    # Build responses
    results = []
    for log in logs:
        user_email = None
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()
            if user:
                user_email = user.email
        
        results.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        ))
    
    return results


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit log statistics for the specified period.
    
    Returns:
    - Total actions by type
    - Most active users
    - Most modified entities
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit statistics"
        )
    
    # Date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(AuditLog).filter(AuditLog.created_at >= start_date)
    
    # Apply organization filter
    if current_user.organization_id != 1:
        from app.models.user import User as UserModel
        org_user_ids = db.query(UserModel.id).filter(
            UserModel.organization_id == current_user.organization_id
        ).all()
        org_user_ids = [uid[0] for uid in org_user_ids]
        
        query = query.filter(
            or_(
                AuditLog.user_id.in_(org_user_ids),
                AuditLog.user_id.is_(None)
            )
        )
    
    all_logs = query.all()
    
    # Count by action
    action_counts = {}
    entity_counts = {}
    user_counts = {}
    
    for log in all_logs:
        # Count actions
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Count entities
        entity_counts[log.entity_type] = entity_counts.get(log.entity_type, 0) + 1
        
        # Count users
        if log.user_id:
            user_counts[log.user_id] = user_counts.get(log.user_id, 0) + 1
    
    # Get top users
    top_users = []
    for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            top_users.append({
                "user_id": user_id,
                "email": user.email,
                "action_count": count
            })
    
    return {
        "period_days": days,
        "total_actions": len(all_logs),
        "actions_by_type": action_counts,
        "entities_by_type": entity_counts,
        "most_active_users": top_users
    }


@router.get("/user/{user_id}")
async def get_user_audit_trail(
    user_id: int,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete audit trail for a specific user.
    
    Useful for investigating user activity or compliance reviews.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view user audit trails"
        )
    
    # Verify user exists and check permissions
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Non-super admin can only view users in their org
    if current_user.organization_id != 1:
        if target_user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view audit trails for users in your organization"
            )
    
    # Build query
    query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
    
    # Apply date filters
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    
    # Get logs
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    # Build responses
    results = []
    for log in logs:
        results.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=target_user.email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        ))
    
    return {
        "user_id": user_id,
        "user_email": target_user.email,
        "total_actions": len(results),
        "audit_trail": results
    }