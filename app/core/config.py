from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, EmailStr, validator
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Investment Dashboard API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Cache Settings
    PRICE_CACHE_TTL: int = 3600  # 1 hour
    
    # Yahoo Finance
    YAHOO_FINANCE_RATE_LIMIT: int = 100
    YAHOO_FINANCE_TIMEOUT: int = 30
    YAHOO_FINANCE_BACKOFF_FACTOR: float = 0.3
    YAHOO_FINANCE_MAX_RETRIES: int = 3
    
    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "America/Sao_Paulo"
    CELERY_ENABLE_UTC: bool = True
    
    # WebSocket
    WEBSOCKET_PRICE_UPDATE_INTERVAL: int = 5  # seconds
    WEBSOCKET_MAX_CONNECTIONS: int = 100
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Export Settings
    MAX_EXPORT_RECORDS: int = 10000
    EXPORT_TEMP_DIR: str = "/tmp/exports"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()