# FastAPI app principal

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.database import init_db, close_db, check_db_health
from app.api.deps import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import routers
from app.api.v1 import auth, dashboard, clients

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting Investment Dashboard API...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Check system health
        health_status = await check_db_health()
        if not health_status:
            logger.warning("Database health check failed during startup")
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Investment Dashboard API...")
    
    try:
        await close_db()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para sistema de investimentos com dashboard em tempo real",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Trusted host middleware (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers"""
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path} - Start")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log response
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} - Error: {e} - {process_time:.4f}s")
        raise

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions globally"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error" if not settings.DEBUG else str(exc),
            "status_code": 500,
            "path": request.url.path
        }
    )

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.VERSION
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        db_healthy = await check_db_health()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": time.time(),
            "version": settings.VERSION,
            "dependencies": {
                "database": "healthy" if db_healthy else "unhealthy",
                "redis": "healthy"  # Would check Redis here
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "api_url": settings.API_V1_STR,
        "status": "running"
    }

# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_STR}/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    clients.router,
    prefix=f"{settings.API_V1_STR}/clients",
    tags=["Clients & Advisors"]
)

# API Info endpoint
@app.get(f"{settings.API_V1_STR}/info")
async def api_info():
    """API information and available endpoints"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "endpoints": {
            "authentication": f"{settings.API_V1_STR}/auth",
            "dashboard": f"{settings.API_V1_STR}/dashboard",
            "clients": f"{settings.API_V1_STR}/clients",
            "assets": f"{settings.API_V1_STR}/assets",
            "allocations": f"{settings.API_V1_STR}/allocations",
            "performance": f"{settings.API_V1_STR}/performance"
        },
        "documentation": {
            "swagger": f"{settings.API_V1_STR}/docs",
            "redoc": f"{settings.API_V1_STR}/redoc",
            "openapi": f"{settings.API_V1_STR}/openapi.json"
        },
        "features": [
            "JWT Authentication",
            "Role-based Access Control",
            "Real-time Price Updates",
            "Portfolio Management",
            "Performance Analytics",
            "Commission Tracking",
            "Data Export",
            "WebSocket Support",
            "Rate Limiting",
            "Caching"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )