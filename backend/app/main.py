from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Import all route modules
from app.routes import auth
from app.routes import organizations
from app.routes import sites
from app.routes import workers
from app.routes import users

# NEW: Import worker feature routes
from app.routes import worker_auth
from app.routes import tasks
from app.routes import attendance
from app.routes import issues

# Import database
from app.database import engine, Base

# Create database tables on startup (if they don't exist)
# Note: We're using Alembic migrations now, so this is mainly for development
# Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("🚀 ClockOut API Starting...")
    print("📊 Database connected")
    print("✅ All routes loaded")
    yield
    # Shutdown
    print("👋 ClockOut API Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="ClockOut API",
    description="GPS-verified farm attendance tracking system for Nigerian agriculture",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==========================================
# CORS CONFIGURATION
# ==========================================
# Allow requests from your Android app and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8081",  # React Native/Expo
        "*"  # Allow all origins (for development - tighten in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


# ==========================================
# HEALTH CHECK ENDPOINT
# ==========================================
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - health check.
    """
    return {
        "message": "ClockOut API is running",
        "version": "2.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "version": "2.0.0"
    }


# ==========================================
# REGISTER ALL ROUTES
# ==========================================

# Core authentication routes (admin/manager)
app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["Authentication"]
)

# Organization management
app.include_router(
    organizations.router,
    prefix="/api/v1",
    tags=["Organizations"]
)

# Sites management (farm locations)
app.include_router(
    sites.router,
    prefix="/api/v1",
    tags=["Sites"]
)

# Workers management (HR records)
app.include_router(
    workers.router,
    prefix="/api/v1",
    tags=["Workers"]
)

# Users management (admin/manager accounts)
app.include_router(
    users.router,
    prefix="/api/v1",
    tags=["Users"]
)

# ==========================================
# NEW: WORKER FEATURE ROUTES
# ==========================================

# Worker authentication (login with employee_id)
app.include_router(
    worker_auth.router,
    prefix="/api/v1",
    tags=["Worker Auth"]
)

# Task management (for both managers and workers)
app.include_router(
    tasks.router,
    prefix="/api/v1",
    tags=["Tasks"]
)

# Auto-attendance with GPS geofencing
app.include_router(
    attendance.router,
    prefix="/api/v1",
    tags=["Attendance"]
)

# Issue reporting (pests, equipment, etc.)
app.include_router(
    issues.router,
    prefix="/api/v1",
    tags=["Issues"]
)


# ==========================================
# GLOBAL EXCEPTION HANDLER
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return a proper JSON response.
    """
    import traceback
    
    # Log the full error (in production, use proper logging)
    print("❌ Unhandled Exception:")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": str(request.url)
        }
    )


# ==========================================
# STARTUP MESSAGE
# ==========================================
@app.on_event("startup")
async def startup_event():
    """
    Print helpful information when the server starts.
    """
    print("\n" + "="*60)
    print("🌾 CLOCKOUT API - Farm Attendance Tracking System")
    print("="*60)
    print(f"📍 API Version: 2.0.0")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🔗 Alternative Docs: http://localhost:8000/redoc")
    print("\n📋 Available Endpoints:")
    print("  • Admin/Manager Auth: /api/v1/auth/*")
    print("  • Worker Auth: /api/v1/auth/worker/*")
    print("  • Organizations: /api/v1/organizations/*")
    print("  • Sites: /api/v1/sites/*")
    print("  • Workers: /api/v1/workers/*")
    print("  • Tasks: /api/v1/tasks/*")
    print("  • Attendance: /api/v1/attendance/*")
    print("  • Issues: /api/v1/issues/*")
    print("="*60 + "\n")


# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )