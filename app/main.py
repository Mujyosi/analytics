from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from fastapi.middleware.cors import CORSMiddleware


from app.config import settings
from app.database import init_tables
from app.redis_client import redis_client
from app.endpoints import router
from app.utils import setup_logging

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI Analytics Server")
    
    # Initialize database tables
    try:
        init_tables()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Test Redis connection
    try:
        redis_client.client.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI Analytics Server")
    # Redis connection will be closed automatically

# Create FastAPI app
app = FastAPI(
    title="Movie Site Analytics API",
    description="Analytics server for collecting movie site events",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Movie Site Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "collect": "/api/v1/collect",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )