"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppException
from app.api.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # --- Startup ---
    setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
    logger.info(f"Starting {settings.APP_NAME} (env={settings.APP_ENV})")

    # Initialize database
    from app.db.session import init_db
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    try:
        from app.db.redis import init_redis
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed (non-critical): {e}")

    # Load tools registry
    from app.tools.registry import tool_registry
    tool_registry.load_from_directory()
    logger.info(f"Loaded {len(tool_registry.list_tools())} tools")

    # Load agent configs
    from app.agents.registry import agent_registry
    agent_registry.load_from_directory(settings.AGENTS_CONFIG_DIR)
    logger.info(f"Loaded {len(agent_registry.list_agents())} agents")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    try:
        from app.db.redis import close_redis
        await close_redis()
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Personal Knowledge Base Agent Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
from app.core.middleware import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy", "app": settings.APP_NAME}


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "detail": exc.detail,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "detail": "An unexpected error occurred" if not settings.DEBUG else str(exc),
            }
        },
    )
