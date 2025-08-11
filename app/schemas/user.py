from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    READ_ONLY = "read_only"

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    role: UserRole = Field(UserRole.READ_ONLY, description="User role")
    is_active: bool = Field(True, description="Whether user is active")

class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=6, max_length=100, description="User password")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v

class UserUpdate(BaseModel):
    """Schema for user updates"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserPasswordUpdate(BaseModel):
    """Schema for password updates"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v

class UserInDB(UserBase):
    """Schema for user from database"""
    id: int
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class User(UserInDB):
    """Public user schema (without sensitive data)"""
    pass

class UserProfile(BaseModel):
    """User profile information"""
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Authentication Schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile

class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile

# User Lists and Pagination
class UserList(BaseModel):
    """Paginated user list response"""
    items: list[User]
    total: int
    page: int
    size: int
    pages: int

class UserStats(BaseModel):
    """User statistics"""
    total_users: int
    active_users: int
    admin_users: int
    read_only_users: int
    recent_logins: int  # Last 30 days