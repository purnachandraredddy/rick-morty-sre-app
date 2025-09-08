"""FastAPI application main module."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.config import settings
from app.database import get_db, create_tables, close_db_connection, check_db_connection
from app.cache import cache
from app.rick_morty_client import rick_morty_client
from app.services import character_service
from app.models import (
    FilteredCharacterResponse, 
    HealthCheckResponse, 
    ErrorResponse
)
from app.metrics import (
    get_metrics, 
    track_request_metrics, 
    update_business_metrics,
    characters_processed,
    api_sync_duration
)
# from app.tracing import setup_tracing  # Will add later when needed

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting application", app_name=settings.app_name, version=settings.app_version)
    
    # Startup
    try:
        # Connect to cache (optional)
        try:
            await cache.connect()
            logger.info("Cache connected successfully")
        except Exception as e:
            logger.warning("Cache connection failed, continuing without cache", error=str(e))
        
        # Create database tables
        await create_tables()
        
        # Initial data sync (in background)
        asyncio.create_task(initial_data_sync())
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    try:
        await cache.disconnect()
        await rick_morty_client.close()
        await close_db_connection()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error("Error during application shutdown", error=str(e))


async def initial_data_sync():
    """Perform initial data synchronization from Rick and Morty API."""
    try:
        logger.info("Starting initial data sync")
        
        # Wait a bit to ensure database is ready
        await asyncio.sleep(5)
        
        from app.database import get_db_session
        
        async with get_db_session() as db:
            start_time = asyncio.get_event_loop().time()
            synced_count = await character_service.sync_characters_from_api(db)
            duration = asyncio.get_event_loop().time() - start_time
            
            # Update metrics
            characters_processed.labels(source="api_sync").inc(synced_count)
            api_sync_duration.observe(duration)
            update_business_metrics(synced_count)
            
            logger.info("Initial data sync completed", synced_count=synced_count, duration=duration)
            
    except Exception as e:
        logger.error("Initial data sync failed", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A production-grade RESTful application integrating with Rick and Morty API",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/healthcheck", response_model=HealthCheckResponse)
@limiter.limit("10/minute")
async def healthcheck(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint with deep health checks.
    
    Checks:
    - Database connectivity
    - Cache connectivity  
    - Rick and Morty API connectivity
    """
    logger.info("Health check requested")
    
    checks = {}
    overall_status = "healthy"
    
    # Database check
    try:
        db_healthy = await check_db_connection()
        checks["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": "Database connection successful" if db_healthy else "Database connection failed"
        }
        if not db_healthy:
            overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database check failed: {str(e)}"
        }
        overall_status = "unhealthy"
    
    # Cache check
    try:
        cache_status = await cache.health_check()
        checks["cache"] = cache_status
        if cache_status["status"] != "healthy":
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    except Exception as e:
        checks["cache"] = {
            "status": "unhealthy",
            "message": f"Cache check failed: {str(e)}"
        }
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    
    # Rick and Morty API check
    try:
        api_status = await rick_morty_client.health_check()
        checks["rick_morty_api"] = api_status
        if api_status["status"] != "healthy":
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    except Exception as e:
        checks["rick_morty_api"] = {
            "status": "unhealthy",
            "message": f"API check failed: {str(e)}"
        }
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    
    # Character count check
    try:
        stats = await character_service.get_stats(db)
        checks["data"] = {
            "status": "healthy",
            "total_characters": stats["total_characters"],
            "last_sync": stats["last_sync"]
        }
    except Exception as e:
        checks["data"] = {
            "status": "unhealthy",
            "message": f"Data check failed: {str(e)}"
        }
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    
    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        checks=checks
    )
    
    # Set appropriate HTTP status code
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service unhealthy")
    
    return response


@app.get("/characters", response_model=dict)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}seconds")
@track_request_metrics
async def get_characters(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    sort: str = "id",
    order: str = "asc",
    db: AsyncSession = Depends(get_db)
):
    """
    Get filtered Rick and Morty characters.
    
    Returns characters that match:
    - Species: Human
    - Status: Alive  
    - Origin: Earth (any variant)
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - sort: Sort field (id, name, created_at)
    - order: Sort order (asc, desc)
    """
    logger.info("Characters requested", page=page, per_page=per_page, sort=sort, order=order)
    
    # Validate parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    
    if per_page < 1 or per_page > 100:
        raise HTTPException(status_code=400, detail="Per page must be between 1 and 100")
    
    if sort not in ["id", "name", "created_at"]:
        raise HTTPException(status_code=400, detail="Sort must be one of: id, name, created_at")
    
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Order must be one of: asc, desc")
    
    try:
        characters, total = await character_service.get_characters(
            db=db,
            page=page,
            per_page=per_page,
            sort_by=sort,
            sort_order=order
        )
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "characters": [char.dict() for char in characters],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        logger.error("Failed to get characters", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/characters/{character_id}", response_model=FilteredCharacterResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}seconds")
@track_request_metrics
async def get_character(
    character_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific character by ID."""
    logger.info("Character requested", character_id=character_id)
    
    if character_id < 1:
        raise HTTPException(status_code=400, detail="Character ID must be >= 1")
    
    try:
        character = await character_service.get_character_by_id(db, character_id)
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return character
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get character", character_id=character_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats")
@limiter.limit("5/minute")
@track_request_metrics
async def get_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Get character statistics."""
    logger.info("Stats requested")
    
    try:
        stats = await character_service.get_stats(db)
        return stats
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/sync")
@limiter.limit("1/minute")
@track_request_metrics
async def sync_characters(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger character synchronization from Rick and Morty API."""
    logger.info("Manual sync requested")
    
    async def sync_task():
        try:
            start_time = asyncio.get_event_loop().time()
            synced_count = await character_service.sync_characters_from_api(db)
            duration = asyncio.get_event_loop().time() - start_time
            
            # Update metrics
            characters_processed.labels(source="manual_sync").inc(synced_count)
            api_sync_duration.observe(duration)
            update_business_metrics(synced_count)
            
            logger.info("Manual sync completed", synced_count=synced_count, duration=duration)
        except Exception as e:
            logger.error("Manual sync failed", error=str(e))
    
    background_tasks.add_task(sync_task)
    
    return {"message": "Synchronization started", "status": "in_progress"}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_data, content_type = await get_metrics()
    return Response(content=metrics_data, media_type=content_type)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    logger.warning("Not found", path=request.url.path, method=request.method)
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    """Custom rate limit handler."""
    logger.warning("Rate limit exceeded", path=request.url.path, method=request.method)
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler."""
    logger.error("Internal server error", path=request.url.path, method=request.method, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )
