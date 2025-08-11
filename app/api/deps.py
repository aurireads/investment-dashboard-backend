from typing import Generator, Optional, Union
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_async_session
from app.core.security import verify_token, UserRole, check_permission
from app.models.user import User
from app.schemas.user import TokenPayload

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

async def get_db() -> Generator[AsyncSession, None, None]:
    """
    Database dependency
    """
    async for session in get_async_session():
        yield session

async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    """
    Get current user from JWT token
    """
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        
        return token_data
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token_data: TokenPayload = Depends(get_current_user_token)
) -> User:
    """
    Get current user from database
    """
    try:
        stmt = select(User).where(User.id == token_data.sub)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user information"
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_role(required_role: str):
    """
    Dependency factory to require specific role
    """
    def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not check_permission(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return role_checker

# Pre-configured role dependencies
get_admin_user = require_role(UserRole.ADMIN)
get_user_with_write_access = require_role(UserRole.ADMIN)  # Only admin can write

async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get user if authenticated, None otherwise (for optional auth endpoints)
    """
    if not credentials:
        return None
        
    try:
        token_data = await get_current_user_token(credentials)
        user = await get_current_user(db, token_data)
        return user
    except HTTPException:
        return None

# Pagination dependencies
class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> PaginationParams:
    """
    Pagination parameters dependency
    """
    return PaginationParams(page=page, size=size)

# Search and filter dependencies
def get_search_params(
    q: Optional[str] = Query(None, min_length=2, max_length=100, description="Search query"),
    sort_by: Optional[str] = Query("id", description="Sort field"),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order"),
):
    """
    Common search parameters
    """
    return {
        "query": q,
        "sort_by": sort_by,
        "sort_order": sort_order
    }

# Rate limiting (using slowapi)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

def get_rate_limiter():
    """Rate limiter dependency"""
    return limiter

# Cache dependencies
import aioredis
from app.core.config import settings

async def get_redis():
    """Redis connection dependency"""
    try:
        redis = aioredis.from_url(settings.REDIS_URL)
        yield redis
    finally:
        await redis.close()

# Common response models
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int):
        """Create paginated response"""
        pages = (total + size - 1) // size  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None

# Validation helpers
def validate_date_range(start_date, end_date):
    """Validate date range"""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

def validate_positive_number(value: Union[int, float], field_name: str):
    """Validate positive number"""
    if value is not None and value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be positive"
        )

# Database transaction helpers
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_transaction(db: AsyncSession):
    """Database transaction context manager"""
    try:
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
        
# Health check dependency
async def check_system_health(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> dict:
    """Check system health"""
    health_status = {
        "database": False,
        "redis": False,
        "timestamp": datetime.now()
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis
    try:
        await redis.ping()
        health_status["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    
    return health_status