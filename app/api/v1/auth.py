from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
import logging

from app.api.deps import get_db, get_current_active_user, get_rate_limiter
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.models.user import User
from app.schemas.user import (
    LoginRequest, LoginResponse, UserCreate, User as UserSchema,
    UserProfile, Token, UserPasswordUpdate
)

logger = logging.getLogger(__name__)
limiter = get_rate_limiter()

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request,  # For rate limiting
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint - authenticate user and return JWT token
    """
    try:
        # Find user by username or email
        stmt = select(User).where(
            (User.username == login_data.username) | 
            (User.email == login_data.username)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.id,
            expires_delta=access_token_expires,
            user_role=user.role
        )
        
        # Update last login
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login=func.now())
        )
        await db.commit()
        
        # Create user profile for response
        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/oauth/token", response_model=Token)
@limiter.limit("5/minute")
async def login_oauth(
    request,  # For rate limiting
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint
    """
    try:
        login_data = LoginRequest(
            username=form_data.username,
            password=form_data.password
        )
        
        response = await login(request, login_data, db)
        
        return Token(
            access_token=response.access_token,
            token_type=response.token_type,
            expires_in=response.expires_in,
            user=response.user
        )
        
    except Exception as e:
        logger.error(f"OAuth login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not authenticate user"
        )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )

@router.post("/change-password")
@limiter.limit("3/minute")
async def change_password(
    request,  # For rate limiting
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Hash new password
        new_hashed_password = get_password_hash(password_data.new_password)
        
        # Update password in database
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(hashed_password=new_hashed_password)
        )
        await db.commit()
        
        logger.info(f"Password changed for user {current_user.id}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_token(
    request,  # For rate limiting
    current_user: User = Depends(get_current_active_user)
):
    """
    Refresh access token
    """
    try:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=current_user.id,
            expires_delta=access_token_expires,
            user_role=current_user.role
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout endpoint (client should discard token)
    """
    # In a more sophisticated setup, we could maintain a blacklist of tokens
    # For now, we just return a success message
    logger.info(f"User {current_user.id} logged out")
    
    return {"message": "Successfully logged out"}

@router.get("/validate-token")
async def validate_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate if current token is still valid
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "role": current_user.role,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }