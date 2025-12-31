from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.worker import Worker
from app.schemas.task import WorkerLoginRequest, WorkerRegisterRequest, WorkerAuthResponse
from app.utils.security import verify_password, get_password_hash, create_access_token, decode_access_token
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth/worker", tags=["Worker Authentication"])

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


# ==========================================
# DEPENDENCY: Get Current User (Admin/Manager)
# ==========================================
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
    Works with existing token format (uses 'sub' field).
    """
    print("=" * 60)
    print("🔍 DEBUG: get_current_user called")
    print(f"🔍 DEBUG: Received token: {token[:50]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        print(f"🔍 DEBUG: Decoded payload: {payload}")
    except Exception as e:
        print(f"❌ DEBUG: Error decoding token: {str(e)}")
        raise credentials_exception
    
    if not payload:
        print("❌ DEBUG: Payload is None or empty")
        raise credentials_exception
    
    # Try to get user_id from token (new format)
    user_id = payload.get("user_id")
    print(f"🔍 DEBUG: user_id from token: {user_id}")
    
    # If not present, use 'sub' (email) to lookup user (existing format)
    if not user_id:
        email = payload.get("sub")
        print(f"🔍 DEBUG: No user_id, using email from 'sub': {email}")
        
        if not email:
            print("❌ DEBUG: No email in payload")
            raise credentials_exception
        
        try:
            user = db.query(User).filter(User.email == email).first()
            print(f"🔍 DEBUG: Database query for email '{email}' returned: {user.email if user else 'None'}")
        except Exception as e:
            print(f"❌ DEBUG: Database error: {str(e)}")
            raise credentials_exception
    else:
        print(f"🔍 DEBUG: Looking up user by user_id: {user_id}")
        try:
            user = db.query(User).filter(User.id == user_id).first()
            print(f"🔍 DEBUG: Database query for user_id {user_id} returned: {user.email if user else 'None'}")
        except Exception as e:
            print(f"❌ DEBUG: Database error: {str(e)}")
            raise credentials_exception
    
    if not user:
        print("❌ DEBUG: User not found in database")
        raise credentials_exception
    
    print(f"✅ DEBUG: Successfully authenticated user: {user.email}, role: {user.role}")
    print("=" * 60)
    return user


# ==========================================
# WORKER LOGIN
# ==========================================
@router.post("/login", response_model=WorkerAuthResponse)
async def worker_login(
    credentials: WorkerLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Worker login with employee_id and password.
    Returns JWT token and worker details.
    """
    print("=" * 60)
    print(f"🔍 DEBUG: Worker login attempt for employee_id: {credentials.employee_id}")
    
    # Find worker by employee_id
    worker = db.query(Worker).filter(
        Worker.employee_id == credentials.employee_id,
        Worker.is_active == True,
        Worker.deleted_at == None
    ).first()
    
    if not worker:
        print(f"❌ DEBUG: Worker not found with employee_id: {credentials.employee_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password"
        )
    
    print(f"✅ DEBUG: Found worker: id={worker.id}, name={worker.name}, user_id={worker.user_id}")
    
    # Check if worker has linked user account
    if not worker.user_id:
        print(f"❌ DEBUG: Worker {worker.id} has no user_id link")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker account not set up for login. Contact your manager."
        )
    
    # Get linked user account
    user = db.query(User).filter(User.id == worker.user_id).first()
    
    if not user:
        print(f"❌ DEBUG: User {worker.user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker account not found"
        )
    
    print(f"✅ DEBUG: Found linked user: email={user.email}")
    
    # Verify password
    try:
        password_valid = verify_password(credentials.password, user.hashed_password)
        print(f"🔍 DEBUG: Password verification: {password_valid}")
    except Exception as e:
        print(f"❌ DEBUG: Password verification error: {str(e)}")
        password_valid = False
    
    if not password_valid:
        print("❌ DEBUG: Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password"
        )
    
    # Update last login
    try:
        if hasattr(worker, 'last_login'):
            worker.last_login = datetime.utcnow()
            db.commit()
            print("✅ DEBUG: Updated last_login timestamp")
    except Exception as e:
        print(f"⚠️ DEBUG: Could not update last_login: {str(e)}")
    
    # Create access token with all needed fields
    token_data = {
        "sub": user.email or f"worker_{worker.employee_id}",
        "user_id": user.id,
        "worker_id": worker.id,
        "role": "worker",
        "organization_id": worker.organization_id
    }
    print(f"🔍 DEBUG: Creating token with data: {token_data}")
    
    try:
        access_token = create_access_token(data=token_data)
        print(f"✅ DEBUG: Token created successfully: {access_token[:50]}...")
    except Exception as e:
        print(f"❌ DEBUG: Error creating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating access token"
        )
    
    # Return token and worker details
    response = WorkerAuthResponse(
        access_token=access_token,
        token_type="bearer",
        worker={
            "id": worker.id,
            "user_id": user.id,
            "name": worker.name,
            "employee_id": worker.employee_id,
            "phone": worker.phone,
            "email": user.email,
            "site_id": worker.site_id,
            "organization_id": worker.organization_id,
            "role": "worker"
        }
    )
    
    print("✅ DEBUG: Worker login successful")
    print("=" * 60)
    return response


# ==========================================
# CREATE WORKER ACCOUNT
# ==========================================
@router.post("/register", response_model=dict)
async def create_worker_with_account(
    worker_data: WorkerRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin/Manager creates a new worker with login credentials.
    Links worker record to user account.
    """
    print("=" * 60)
    print(f"🔍 DEBUG: Worker registration attempt by user: {current_user.email}")
    print(f"🔍 DEBUG: Worker data: employee_id={worker_data.employee_id}, name={worker_data.name}")
    
    # Verify current user is admin or manager
    if current_user.role not in ["admin", "manager"]:
        print(f"❌ DEBUG: User role '{current_user.role}' not authorized")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create worker accounts"
        )
    
    print(f"✅ DEBUG: User authorized (role: {current_user.role})")
    
    # Check if employee_id already exists
    existing_worker = db.query(Worker).filter(
        Worker.employee_id == worker_data.employee_id,
        Worker.organization_id == current_user.organization_id
    ).first()
    
    if existing_worker:
        print(f"❌ DEBUG: Employee ID {worker_data.employee_id} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee ID {worker_data.employee_id} already exists"
        )
    
    print(f"✅ DEBUG: Employee ID {worker_data.employee_id} is available")
    
    # Check if email already exists (if provided)
    if worker_data.email:
        existing_user = db.query(User).filter(User.email == worker_data.email).first()
        if existing_user:
            print(f"❌ DEBUG: Email {worker_data.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    print(f"✅ DEBUG: Email is available or not provided")
    
    # Create user account
    print(f"🔍 DEBUG: Creating user account...")
    try:
        hashed_pw = get_password_hash(worker_data.password)
        print(f"✅ DEBUG: Password hashed successfully")
    except Exception as e:
        print(f"❌ DEBUG: Error hashing password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password"
        )
    
    new_user = User(
        email=worker_data.email or f"{worker_data.employee_id}@worker.local",
        hashed_password=hashed_pw,
        full_name=worker_data.name,
        role="worker",
        organization_id=current_user.organization_id
    )
    
    # Set user_mode if the field exists
    if hasattr(new_user, 'user_mode'):
        new_user.user_mode = "worker"
        print("✅ DEBUG: Set user_mode to 'worker'")
    
    # Set assigned_sites if the field exists
    if hasattr(new_user, 'assigned_sites'):
        new_user.assigned_sites = [worker_data.site_id]
        print(f"✅ DEBUG: Set assigned_sites to [{worker_data.site_id}]")
    
    try:
        db.add(new_user)
        db.flush()  # Get user.id
        print(f"✅ DEBUG: User created with id: {new_user.id}")
    except Exception as e:
        print(f"❌ DEBUG: Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    # Create worker record
    print(f"🔍 DEBUG: Creating worker record...")
    new_worker = Worker(
        user_id=new_user.id,
        employee_id=worker_data.employee_id,
        name=worker_data.name,
        phone=worker_data.phone,
        site_id=worker_data.site_id,
        organization_id=current_user.organization_id,
        is_active=True
    )
    
    # Set created_by if the field exists
    if hasattr(new_worker, 'created_by'):
        new_worker.created_by = current_user.id
        print(f"✅ DEBUG: Set created_by to {current_user.id}")
    
    try:
        db.add(new_worker)
        db.commit()
        db.refresh(new_worker)
        print(f"✅ DEBUG: Worker created with id: {new_worker.id}")
    except Exception as e:
        print(f"❌ DEBUG: Error creating worker: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    response = {
        "message": "Worker account created successfully",
        "worker": {
            "id": new_worker.id,
            "user_id": new_user.id,
            "employee_id": new_worker.employee_id,
            "name": new_worker.name,
            "site_id": new_worker.site_id
        }
    }
    
    print(f"✅ DEBUG: Worker registration successful: {response}")
    print("=" * 60)
    return response


# ==========================================
# PASSWORD RESET
# ==========================================
@router.post("/password-reset-request")
async def request_password_reset(
    employee_id: str,
    email: str,
    db: Session = Depends(get_db)
):
    """
    Worker requests password reset.
    Requires both employee_id and email to match.
    """
    # Find worker
    worker = db.query(Worker).filter(
        Worker.employee_id == employee_id,
        Worker.is_active == True
    ).first()
    
    if not worker or not worker.user_id:
        # Don't reveal if worker exists for security
        return {"message": "If the employee ID and email match, a reset link will be sent"}
    
    # Get user account
    user = db.query(User).filter(
        User.id == worker.user_id,
        User.email == email
    ).first()
    
    if not user:
        return {"message": "If the employee ID and email match, a reset link will be sent"}
    
    # Generate reset token (implement token generation)
    # TODO: Send email with reset link
    
    return {"message": "If the employee ID and email match, a reset link will be sent"}


# ==========================================
# DEPENDENCY: Get Current Worker
# ==========================================
async def get_current_worker(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Worker:
    """
    Validate JWT token and return current worker.
    """
    print("=" * 60)
    print("🔍 DEBUG: get_current_worker called")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        print(f"🔍 DEBUG: Decoded payload: {payload}")
    except Exception as e:
        print(f"❌ DEBUG: Error decoding token: {str(e)}")
        raise credentials_exception
    
    if not payload:
        print("❌ DEBUG: Payload is None or empty")
        raise credentials_exception
    
    worker_id = payload.get("worker_id")
    print(f"🔍 DEBUG: worker_id from token: {worker_id}")
    
    if not worker_id:
        print("❌ DEBUG: No worker_id in token")
        raise credentials_exception
    
    try:
        worker = db.query(Worker).filter(
            Worker.id == worker_id,
            Worker.is_active == True
        ).first()
        print(f"🔍 DEBUG: Database query for worker_id {worker_id} returned: {worker.name if worker else 'None'}")
    except Exception as e:
        print(f"❌ DEBUG: Database error: {str(e)}")
        raise credentials_exception
    
    if not worker:
        print("❌ DEBUG: Worker not found in database")
        raise credentials_exception
    
    print(f"✅ DEBUG: Successfully authenticated worker: {worker.name} ({worker.employee_id})")
    print("=" * 60)
    return worker