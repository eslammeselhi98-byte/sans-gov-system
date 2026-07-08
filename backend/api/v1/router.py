from fastapi import APIRouter

from .auth import router as auth_router
from .projects import router as projects_router
from .schedule import router as schedule_router
from .boq import router as boq_router
from .cost import router as cost_router
from .employees import router as employees_router
from .attendance import router as attendance_router
from .daily_reports import router as reports_router
from .documents import router as documents_router
from .equipment import router as equipment_router
from .materials import router as materials_router
from .risks import router as risks_router
from .dashboard import router as dashboard_router
from .ai import router as ai_router
from .uploads import router as uploads_router

api_router = APIRouter()

api_router.include_router(auth_router,       prefix="/auth",         tags=["Authentication"])
api_router.include_router(dashboard_router,  prefix="/dashboard",    tags=["Dashboard"])
api_router.include_router(projects_router,   prefix="/projects",     tags=["Projects"])
api_router.include_router(schedule_router,   prefix="/schedule",     tags=["Schedule & WBS"])
api_router.include_router(boq_router,        prefix="/boq",          tags=["BOQ"])
api_router.include_router(cost_router,       prefix="/cost",         tags=["Cost Control"])
api_router.include_router(employees_router,  prefix="/employees",    tags=["Employees"])
api_router.include_router(attendance_router, prefix="/attendance",   tags=["Attendance"])
api_router.include_router(reports_router,    prefix="/reports",      tags=["Daily Reports"])
api_router.include_router(documents_router,  prefix="/documents",    tags=["Document Control"])
api_router.include_router(equipment_router,  prefix="/equipment",    tags=["Equipment"])
api_router.include_router(materials_router,  prefix="/materials",    tags=["Materials"])
api_router.include_router(risks_router,      prefix="/risks",        tags=["Risk Register"])
api_router.include_router(ai_router,         prefix="/ai",           tags=["AI Engine"])
api_router.include_router(uploads_router,    prefix="/uploads",      tags=["File Uploads"])
