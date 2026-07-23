import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.rate_limit import RateLimitMiddleware
from app.core.timing import ResponseTimeMiddleware
from app.routers import (
    access_control,
    admin,
    admin_config,
    admin_extra,
    admin_ops,
    analytics,
    approval_extra,
    approvals,
    audit,
    auth,
    collab_extra,
    comments,
    compliance,
    compliance_frameworks,
    contact,
    documents_bulk,
    documents_extra,
    documents,
    filter_templates,
    governance,
    insights,
    insights_extra,
    knowledge,
    notifications,
    predictions,
    projects,
    reviews,
    search,
    search_history,
    teams,
)

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

# Middleware: gzip response compression (T-3007)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware: X-Response-Time-Ms header (T-3008)
app.add_middleware(ResponseTimeMiddleware)

# Middleware: token-bucket rate limiting (T-3028)
app.add_middleware(RateLimitMiddleware)

# Include routers
# NOTE: documents_extra / documents_bulk register static paths under
# /api/v1/documents (e.g. GET /duplicates, POST /bulk-review) and MUST be
# included before documents.router -- FastAPI matches routes in
# registration order, so documents.router's GET /{doc_id} would otherwise
# swallow /duplicates as doc_id="duplicates" (422 on UUID parse) before
# documents_extra ever sees the request.
app.include_router(access_control.router)
app.include_router(admin.router)
app.include_router(admin_config.router)
app.include_router(admin_extra.router)
app.include_router(admin_ops.router)
app.include_router(analytics.router)
app.include_router(approval_extra.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(auth.router)
app.include_router(collab_extra.router)
app.include_router(comments.router)
app.include_router(compliance.router)
app.include_router(compliance_frameworks.router)
app.include_router(contact.router)
app.include_router(documents_extra.router)
app.include_router(documents_bulk.router)
app.include_router(documents.router)
app.include_router(filter_templates.router)
app.include_router(governance.router)
app.include_router(insights.router)
app.include_router(insights.compare_router)
app.include_router(insights_extra.router)
app.include_router(knowledge.router)
app.include_router(notifications.router)
app.include_router(predictions.router)
app.include_router(projects.router)
app.include_router(reviews.router)
app.include_router(search.router)
app.include_router(search_history.router)
app.include_router(teams.router)


# Health Check Endpoint. /api/v1/health alias: the VPS reverse proxy only
# routes /api/* to this container, so external uptime monitors need the
# aliased path -- bare /health is only reachable inside the network.
@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
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
