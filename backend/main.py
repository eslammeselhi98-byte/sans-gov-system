from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import time
import os

from core.config import settings
from core.database import check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("🚀 SANS PMS Backend starting up...")
    logger.info(f"   Environment : {settings.ENVIRONMENT}")
    logger.info(f"   Version     : {settings.VERSION}")

    # Verify database
    if await check_db_connection():
        logger.info("   Database    : ✅ Connected")
    else:
        logger.error("   Database    : ❌ Connection failed!")

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)

    logger.info("🟢 SANS PMS is ready.")
    yield
    logger.info("🔴 SANS PMS shutting down...")


app = FastAPI(
    title="SANS PMS API",
    description="""
## SANS International Company — Construction Project Management System

### Features
- 🏗️ Multi-project management
- 📅 Schedule (WBS / Primavera XER import)
- 💰 BOQ & Cost Control with EVM
- 👷 HR & Attendance
- 📋 Daily Reports
- 🤖 AI Decision Engine (Claude)
- 📱 Telegram Bot integration
- 📄 Document Control

### Auth
All endpoints require a Bearer JWT token. Obtain it from `/api/v1/auth/login`.
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# ─── Middleware ───────────────────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    if response.status_code >= 400:
        logger.warning(f"{request.method} {request.url.path} → {response.status_code}")
    return response


# ─── Static files ─────────────────────────────────────────────

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ─── Global exception handler ────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again."},
    )


# ─── Health check ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    db_ok = await check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "disconnected",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "SANS PMS API",
        "message_ar": "نظام إدارة مشاريع سانس",
        "version": settings.VERSION,
        "docs": "/docs",
    }


# ─── API Routers ─────────────────────────────────────────────

from api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")
