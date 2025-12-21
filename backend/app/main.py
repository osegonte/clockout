from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base

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

# ✅ STAGE 2.1: Organizations API
from app.routes import organizations
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])

# ✅ STAGE 2.2: Users & Managers API
from app.routes import users
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "ClockOut API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}