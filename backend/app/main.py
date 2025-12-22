from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from app.routes import checkpoints, audit, timeline


# Import routes
from app.routes import auth, sites, workers, events

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS - simplified version
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])

# ✅ STAGE 2.3: Worker Analytics & Enhancements (MUST come BEFORE workers router!)
from app.routes import worker_analytics
app.include_router(worker_analytics.router, prefix=f"{settings.API_V1_STR}/workers", tags=["worker-analytics"])

app.include_router(sites.router, prefix=f"{settings.API_V1_STR}/sites", tags=["sites"])
app.include_router(workers.router, prefix=f"{settings.API_V1_STR}/workers", tags=["workers"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["events"])
app.include_router(checkpoints.router, prefix=f"{settings.API_V1_STR}/checkpoints", tags=["checkpoints"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])
app.include_router(timeline.router, prefix=f"{settings.API_V1_STR}/timeline", tags=["timeline"])

# ✅ STAGE 2.1: Organizations API
from app.routes import organizations
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])

# ✅ STAGE 2.2: Users & Managers API
from app.routes import users
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])

from app.routes import reports
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])

@app.get("/")
async def root():
    return {"message": "ClockOut API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}