"""
RF Spectrum Monitor - FastAPI Application

Main entry point for the REST API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import time

from ..core.config import settings
from ..core.task_queue import get_task_manager
from ..core.survey_manager import get_survey_manager
from ..sdr import get_device_registry
from ..storage.database import init_db
from .routes import devices, surveys, spectrum, export, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup and shutdown logic.
    """
    # Startup
    logger.info("Starting RF Spectrum Monitor API...")
    init_db()
    logger.info("Database initialized")

    # Initialize task manager (starts worker threads)
    task_manager = get_task_manager()
    logger.info("Task manager initialized")

    yield

    # Shutdown
    logger.info("Shutting down RF Spectrum Monitor API...")

    # Stop any running surveys
    survey_manager = get_survey_manager()
    if survey_manager.get_state():
        logger.info("Stopping active survey...")
        survey_manager.stop_survey()

    # Close all open SDR devices
    device_registry = get_device_registry()
    device_registry.close_all()
    logger.info("Device registry shutdown complete")

    # Shutdown task manager
    task_manager.shutdown(wait=True)
    logger.info("Task manager shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="RF Spectrum Monitor API",
    description="""
    RESTful API for RF spectrum monitoring, survey management, and data analysis.

    ## Features

    * **Devices** - Manage SDR hardware (HackRF, RTL-SDR)
    * **Surveys** - Create and manage spectrum surveys
    * **Spectrum** - Query measurements and perform scans
    * **Export** - Export data to CSV and GeoPackage formats

    ## Authentication

    Currently no authentication required (development mode).
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(
    devices.router,
    prefix="/api/devices",
    tags=["Devices"]
)

app.include_router(
    surveys.router,
    prefix="/api/surveys",
    tags=["Surveys"]
)

app.include_router(
    spectrum.router,
    prefix="/api/spectrum",
    tags=["Spectrum"]
)

app.include_router(
    export.router,
    prefix="/api/export",
    tags=["Export"]
)

app.include_router(
    websocket.router,
    prefix="/ws",
    tags=["WebSocket"]
)


# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }


@app.get("/api", tags=["Root"])
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "devices": "/api/devices",
            "surveys": "/api/surveys",
            "spectrum": "/api/spectrum",
            "export": "/api/export"
        },
        "websocket": {
            "spectrum": "/ws/spectrum",
            "survey": "/ws/survey/{survey_id}",
            "signals": "/ws/signals"
        }
    }
