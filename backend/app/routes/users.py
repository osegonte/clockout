from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user, get_password_hash

router = APIRouter()


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "manager"  # admin, manager
    user_mode: str = "manager"  # manager, admin
    assigned_site_ids: Optional[List[int]] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    user_mode: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    user_mode: str
    is_active: bool
    organization_id: int
    assigned_sites: List[int]
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class SiteAssignment(BaseModel):
    site_ids: List[int]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_user_assigned_sites(user_id: int, db: Session) -> List[int]:
    """Get list of site IDs assigned to a user"""
    result = db.execute(
        text("SELECT site_id FROM user_sites WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    return [row[0] for row in result]


def assign_user_to_sites(user_id: int, site_ids: List[int], db: Session):
    """Assign user to multiple sites (replaces existing assignments)"""
    # Remove existing assignments
    db.execute(
        text("DELETE FROM user_sites WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    
    # Add new assignments
    for site_id in site_ids:
        db.execute(
            text("INSERT INTO user_sites (user_id, site_id) VALUES (:user_id, :site_id)"),
            {"user_id": user_id, "site_id": site_id}
        )
    
    db.commit()


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user/manager
    
    Only admins can create users
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create users"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role and mode
    valid_roles = ["admin", "manager"]
    valid_modes = ["admin", "manager"]
    
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    if user_data.user_mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid user_mode. Must be one of: {', '.join(valid_modes)}"
        )
    
    # Create user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        user_mode=user_data.user_mode,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Assign to sites if provided
    assigned_sites = []
    if user_data.assigned_site_ids:
        assign_user_to_sites(new_user.id, user_data.assigned_site_ids, db)
        assigned_sites = user_data.assigned_site_ids
    
    # Return response with assigned sites
    response_data = UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        user_mode=new_user.user_mode,
        is_active=new_user.is_active,
        organization_id=new_user.organization_id,
        assigned_sites=assigned_sites,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )
    
    return response_data


@router.get("/", response_model=List[UserResponse])
async def list_users(
    organization_id: Optional[int] = None,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all users in organization
    
    Filters out soft-deleted users by default
    """
    # Use current user's organization if not specified
    org_id = organization_id or current_user.organization_id
    
    # Check permissions
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = db.query(User).filter(
        User.organization_id == org_id,
        User.deleted_at.is_(None)
    )
    
    if not include_inactive:
        query = query.filter(User.is_active == True)
    
    users = query.order_by(User.created_at.desc()).all()
    
    # Build response with assigned sites
    response = []
    for user in users:
        assigned_sites = get_user_assigned_sites(user.id, db)
        response.append(UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            user_mode=user.user_mode,
            is_active=user.is_active,
            organization_id=user.organization_id,
            assigned_sites=assigned_sites,
            created_at=user.created_at,
            last_login=user.last_login
        ))
    
    return response


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific user details
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check permissions
    if current_user.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    assigned_sites = get_user_assigned_sites(user.id, db)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        user_mode=user.user_mode,
        is_active=user.is_active,
        organization_id=user.organization_id,
        assigned_sites=assigned_sites,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user details
    
    Only admins can update users
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check same organization
    if current_user.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    user.updated_by = current_user.id
    user.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(user)
    
    assigned_sites = get_user_assigned_sites(user.id, db)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        user_mode=user.user_mode,
        is_active=user.is_active,
        organization_id=user.organization_id,
        assigned_sites=assigned_sites,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/{user_id}/assign-sites", response_model=UserResponse)
async def assign_sites_to_user(
    user_id: int,
    assignment: SiteAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign user to specific sites
    
    Replaces existing site assignments
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign sites")
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check same organization
    if current_user.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Assign sites
    assign_user_to_sites(user_id, assignment.site_ids, db)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        user_mode=user.user_mode,
        is_active=user.is_active,
        organization_id=user.organization_id,
        assigned_sites=assignment.site_ids,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/{user_id}", status_code=200)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete user (set deleted_at timestamp)
    
    Only admins can delete users
    Cannot delete yourself
    """
    # Check permissions
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    # Cannot delete yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check same organization
    if current_user.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Soft delete
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    user.updated_by = current_user.id
    user.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {
        "message": "User deleted successfully",
        "user_id": user_id,
        "email": user.email
    }