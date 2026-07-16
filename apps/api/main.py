import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, documents, reviews

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting EDGP API server...")
    yield
    # Shutdown
    logger.info("🛑 Shutting down EDGP API server...")


# Create FastAPI app
app = FastAPI(
    title="Enterprise Document Governance Platform API",
    description="AI-powered document review and governance platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Middleware: CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: Trusted Hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
)

# Include routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(reviews.router)


# Health Check Endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "edgp-api",
        "version": "1.0.0"
    }


# Root Endpoint
@app.get("/", tags=["root"])
async def root():
    """Welcome message."""
    return {
        "message": "Enterprise Document Governance Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi_schema": "/openapi.json",
        "health": "/health",
    }


# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("API_ENV") == "development",
        log_level="info"
    )
