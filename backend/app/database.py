from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure engine with proper SSL and connection pool settings
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pool settings
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=5,         # Connection pool size
    max_overflow=10,     # Max connections beyond pool_size
    # Timeout settings
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)