from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 1 week
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ClockOut API"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()