from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import init_db
from app.routes import auth, sites, workers, events

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware (allows web dashboard to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(sites.router, prefix=f"{settings.API_V1_STR}/sites", tags=["sites"])
app.include_router(workers.router, prefix=f"{settings.API_V1_STR}/workers", tags=["workers"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["events"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "ClockOut API",
        "version": "1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}