from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr  # UPDATED: Added EmailStr

from app.database import get_db
from app.models.user import User, Organization  # UPDATED: Added Organization
from app.core.config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# Pydantic schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class TokenData(BaseModel):
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    mode: str  # Still "mode" in API response for Android
    assigned_sites: List[int]
    
    class Config:
        from_attributes = True


# NEW: Registration schema
class OrganizationRegistration(BaseModel):
    organization_name: str
    admin_name: str
    email: EmailStr
    password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency to get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_assigned_sites(user_id: int, db: Session) -> List[int]:
    """Get list of site IDs assigned to a user"""
    from sqlalchemy import text
    result = db.execute(
        text("SELECT site_id FROM user_sites WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    return [row[0] for row in result]


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns JWT token + user info"""
    # Find user
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Get assigned sites
    assigned_sites = []
    if user.user_mode == "manager":  # CHANGED: mode → user_mode
        assigned_sites = get_assigned_sites(user.id, db)
    elif user.user_mode == "admin":  # CHANGED: mode → user_mode
        # Admins see all sites in their organization
        from app.models.site import Site
        sites = db.query(Site).filter(Site.organization_id == user.organization_id).all()
        assigned_sites = [site.id for site in sites]
    
    # Create token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "mode": user.user_mode,  # CHANGED: Send as "mode" for API compatibility
            "assigned_sites": assigned_sites,
            "organization_id": user.organization_id
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info"""
    assigned_sites = []
    if current_user.user_mode == "manager":  # CHANGED: mode → user_mode
        assigned_sites = get_assigned_sites(current_user.id, db)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        mode=current_user.user_mode,  # CHANGED: Map back to "mode"
        assigned_sites=assigned_sites
    )


# NEW: Organization Registration Endpoint
@router.post("/register/organization", status_code=201)
async def register_organization(
    registration: OrganizationRegistration,
    db: Session = Depends(get_db)
):
    """
    Register a new organization with an admin user
    
    Creates:
    1. Organization with trial subscription
    2. Admin user for that organization
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == registration.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check if organization name already exists
    existing_org = db.query(Organization).filter(Organization.name == registration.organization_name).first()
    if existing_org:
        raise HTTPException(
            status_code=400,
            detail="Organization name already taken"
        )
    
    # Create organization with trial subscription
    new_org = Organization(
        name=registration.organization_name,
        owner_name=registration.admin_name,
        owner_email=registration.email,
        subscription_plan="free",
        subscription_status="trial",
        max_sites=1,
        max_workers=10,
        max_managers=2
    )
    db.add(new_org)
    db.flush()  # Get the org.id without committing
    
    # Create admin user
    new_user = User(
        email=registration.email,
        hashed_password=get_password_hash(registration.password),
        full_name=registration.admin_name,
        role="admin",
        user_mode="admin",
        organization_id=new_org.id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_org)
    db.refresh(new_user)
    
    return {
        "message": "Organization created successfully",
        "organization_id": new_org.id,
        "organization_name": new_org.name,
        "admin_email": new_user.email,
        "subscription_status": new_org.subscription_status
    }


@router.post("/register")
async def register_test_user(
    email: str,
    password: str,
    full_name: str,
    mode: str = "manager",
    assigned_site_ids: Optional[List[int]] = None,
    organization_id: int = 1,
    db: Session = Depends(get_db)
):
    """Test endpoint to create users"""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role="manager" if mode == "manager" else "admin",
        user_mode=mode,  # CHANGED: mode → user_mode
        organization_id=organization_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign sites
    if assigned_site_ids:
        from sqlalchemy import text
        for site_id in assigned_site_ids:
            db.execute(
                text("INSERT INTO user_sites (user_id, site_id) VALUES (:user_id, :site_id)"),
                {"user_id": user.id, "site_id": site_id}
            )
        db.commit()
    
    return {
        "message": "User created",
        "email": user.email,
        "mode": user.user_mode,  # CHANGED
        "assigned_sites": assigned_site_ids or []
    }