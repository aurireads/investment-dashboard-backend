from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    user_role: str = "read_only"
) -> str:
    """
    Create JWT access token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": user_role,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not hash password"
        )

def verify_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp is None:
            return None
            
        if datetime.utcnow().timestamp() > exp:
            return None
            
        # Check if it's an access token
        if payload.get("type") != "access":
            return None
            
        return payload
        
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

def decode_token(token: str) -> dict:
    """
    Decode JWT token without verification (for debugging)
    """
    try:
        return jwt.decode(
            token, 
            options={"verify_signature": False}
        )
    except Exception as e:
        logger.error(f"Token decoding error: {e}")
        return {}

# Role-based access control
class UserRole:
    ADMIN = "admin"
    READ_ONLY = "read_only"
    
    @classmethod
    def get_all_roles(cls):
        return [cls.ADMIN, cls.READ_ONLY]
    
    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        return role in cls.get_all_roles()

def check_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user has required permission
    Admin has access to everything
    """
    if user_role == UserRole.ADMIN:
        return True
    
    if required_role == UserRole.READ_ONLY:
        return user_role in [UserRole.ADMIN, UserRole.READ_ONLY]
    
    return user_role == required_role

# Security utilities
def generate_api_key() -> str:
    """
    Generate API key for external integrations
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data showing only last few characters
    """
    if len(data) <= visible_chars:
        return "*" * len(data)
    
    return "*" * (len(data) - visible_chars) + data[-visible_chars:]