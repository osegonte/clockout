from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import Organization, User
from app.models.site import Site
from app.models.worker import Worker
from app.routes.auth import get_current_user

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class OrganizationRegister(BaseModel):
    name: str
    admin_email: str
    admin_password: str


class OrganizationResponse(BaseModel):
    id: int
    name: str
    owner_name: Optional[str]
    owner_email: Optional[str]
    owner_phone: Optional[str]
    subscription_plan: str
    subscription_status: str
    subscription_start_date: Optional[datetime]
    subscription_end_date: Optional[datetime]
    max_sites: int
    max_workers: int
    max_managers: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None


class PlanUpdate(BaseModel):
    plan: str  # free, starter, pro, enterprise
    status: Optional[str] = None  # trial, active, suspended, cancelled


class UsageStats(BaseModel):
    current_sites: int
    current_workers: int
    current_managers: int
    max_sites: int
    max_workers: int
    max_managers: int
    sites_remaining: int
    workers_remaining: int
    managers_remaining: int
    subscription_plan: str
    subscription_status: str
    days_until_expiry: Optional[int]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_plan_limits(plan: str) -> dict:
    """Get the limits for each subscription plan"""
    plans = {
        "free": {"max_sites": 1, "max_workers": 10, "max_managers": 2},
        "starter": {"max_sites": 3, "max_workers": 50, "max_managers": 5},
        "pro": {"max_sites": 10, "max_workers": 200, "max_managers": 20},
        "enterprise": {"max_sites": 999, "max_workers": 9999, "max_managers": 100}
    }
    return plans.get(plan, plans["free"])


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/register")
async def register_organization(
    org_data: OrganizationRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new organization with an admin user
    
    This is a public endpoint - no authentication required
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == org_data.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check if organization name already exists
    existing_org = db.query(Organization).filter(Organization.name == org_data.name).first()
    if existing_org:
        raise HTTPException(
            status_code=400,
            detail="Organization name already taken"
        )
    
    # Create organization with free plan limits
    free_limits = get_plan_limits("free")
    new_org = Organization(
        name=org_data.name,
        owner_email=org_data.admin_email,
        subscription_plan="free",
        subscription_status="trial",
        subscription_start_date=datetime.now(timezone.utc),
        subscription_end_date=datetime.now(timezone.utc) + timedelta(days=30),  # 30 day trial
        max_sites=free_limits["max_sites"],
        max_workers=free_limits["max_workers"],
        max_managers=free_limits["max_managers"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(new_org)
    db.flush()  # Get the organization ID
    
    # Create admin user
    hashed_password = pwd_context.hash(org_data.admin_password)
    admin_user = User(
        email=org_data.admin_email,
        hashed_password=hashed_password,
        full_name=f"{org_data.name} Admin",
        organization_id=new_org.id,
        role="admin",
        user_mode="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(new_org)
    
    return {
        "message": "Organization registered successfully",
        "organization_id": new_org.id,
        "admin_email": org_data.admin_email
    }


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get organization details
    
    Only users within the organization can access this
    """
    # Check if user belongs to this organization
    if current_user.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this organization"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update organization information
    
    Only admins can update organization details
    """
    # Check permissions
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update organization details"
        )
    
    # Get organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Update fields
    update_data = org_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    
    org.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(org)
    
    return org


@router.put("/{org_id}/plan", response_model=OrganizationResponse)
async def update_subscription_plan(
    org_id: int,
    plan_update: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update subscription plan
    
    Changes plan and adjusts limits accordingly
    """
    # Check permissions
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.role != "admin" and current_user.user_mode != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change plans")
    
    # Validate plan
    valid_plans = ["free", "starter", "pro", "enterprise"]
    if plan_update.plan not in valid_plans:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}"
        )
    
    # Get organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get new plan limits
    new_limits = get_plan_limits(plan_update.plan)
    
    # Update plan
    org.subscription_plan = plan_update.plan
    if plan_update.status:
        org.subscription_status = plan_update.status
    
    # Update limits
    org.max_sites = new_limits["max_sites"]
    org.max_workers = new_limits["max_workers"]
    org.max_managers = new_limits["max_managers"]
    
    # If upgrading from trial/free to paid, set dates
    if plan_update.plan != "free" and org.subscription_status == "trial":
        org.subscription_status = "active"
        org.subscription_start_date = datetime.now(timezone.utc)
        # Set expiry to 1 year from now
        org.subscription_end_date = datetime.now(timezone.utc) + timedelta(days=365)
    
    org.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(org)
    
    return org


@router.get("/{org_id}/stats", response_model=UsageStats)
async def get_organization_stats(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get organization usage statistics
    
    Shows current usage vs plan limits
    """
    # Check permissions
    if current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Count current usage
    current_sites = db.query(func.count(Site.id)).filter(
        Site.organization_id == org_id,
        Site.deleted_at.is_(None)
    ).scalar() or 0
    
    current_workers = db.query(func.count(Worker.id)).filter(
        Worker.organization_id == org_id,
        Worker.deleted_at.is_(None),
        Worker.is_active == True
    ).scalar() or 0
    
    # Count managers (users with manager role or mode)
    current_managers = db.query(func.count(User.id)).filter(
        User.organization_id == org_id,
        User.is_active == True
    ).filter(
        (User.user_mode == "manager") | (User.role == "manager")
    ).scalar() or 0
    
    # Calculate days until expiry
    days_until_expiry = None
    if org.subscription_end_date:
        now = datetime.now(timezone.utc)
        delta = org.subscription_end_date - now
        days_until_expiry = max(0, delta.days)
    
    return UsageStats(
        current_sites=current_sites,
        current_workers=current_workers,
        current_managers=current_managers,
        max_sites=org.max_sites,
        max_workers=org.max_workers,
        max_managers=org.max_managers,
        sites_remaining=max(0, org.max_sites - current_sites),
        workers_remaining=max(0, org.max_workers - current_workers),
        managers_remaining=max(0, org.max_managers - current_managers),
        subscription_plan=org.subscription_plan,
        subscription_status=org.subscription_status,
        days_until_expiry=days_until_expiry
    )