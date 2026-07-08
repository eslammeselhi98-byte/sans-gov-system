from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timezone
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.core import (
    DailyReport, DailyReportActivity, DailyReportManpower,
    DailyReportEquipment, DailyReportMaterial, DailyReportPhoto,
)

router = APIRouter()


class ActivityEntry(BaseModel):
    activity_id: Optional[UUID] = None
    activity_name: Optional[str] = None
    work_done: Optional[str] = None
    progress_today: float = 0
    crew_count: int = 0


class ManpowerEntry(BaseModel):
    employee_id: Optional[UUID] = None
    position_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    hours_worked: float = 8
    overtime_hours: float = 0


class EquipmentEntry(BaseModel):
    equipment_id: Optional[UUID] = None
    equipment_name: Optional[str] = None
    activity_id: Optional[UUID] = None
    hours_worked: float = 0
    fuel_consumed: float = 0


class MaterialEntry(BaseModel):
    material_id: Optional[UUID] = None
    material_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None


class DailyReportCreate(BaseModel):
    project_id: UUID
    report_date: date
    weather_condition: str = "sunny"
    weather_temp: Optional[int] = None
    weather_humidity: Optional[int] = None
    site_conditions: Optional[str] = None
    work_performed: Optional[str] = None
    work_performed_ar: Optional[str] = None
    delays_description: Optional[str] = None
    constraints_description: Optional[str] = None
    safety_incidents: Optional[str] = None
    overall_progress: Optional[float] = None
    status: str = "draft"
    activities: List[ActivityEntry] = []
    manpower: List[ManpowerEntry] = []
    equipment: List[EquipmentEntry] = []
    materials: List[MaterialEntry] = []


class ApprovalAction(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None


def _report_summary(r: DailyReport) -> dict:
    return {
        "id": str(r.id),
        "project_id": str(r.project_id),
        "report_date": r.report_date.isoformat(),
        "weather_condition": r.weather_condition,
        "weather_temp": r.weather_temp,
        "work_performed": r.work_performed,
        "delays_description": r.delays_description,
        "overall_progress": float(r.overall_progress) if r.overall_progress else None,
        "status": r.status,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_daily_report(body: DailyReportCreate, current_user: CurrentUser, db: DB):
    """Create or update today's daily report (one per project per day)."""
    existing = await db.execute(
        select(DailyReport).where(
            DailyReport.project_id == body.project_id,
            DailyReport.report_date == body.report_date,
        )
    )
    report = existing.scalar_one_or_none()

    fields = body.model_dump(exclude={"activities", "manpower", "equipment", "materials"})

    if report:
        if report.status == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit an approved report")
        for k, v in fields.items():
            setattr(report, k, v)
    else:
        report = DailyReport(submitted_by=current_user.id, **fields)
        db.add(report)
        await db.flush()

    if body.status == "submitted":
        report.submitted_at = datetime.now(timezone.utc)

    # Replace child rows
    for model, items in [
        (DailyReportActivity, body.activities),
        (DailyReportManpower, body.manpower),
        (DailyReportEquipment, body.equipment),
        (DailyReportMaterial, body.materials),
    ]:
        await db.execute(model.__table__.delete().where(model.report_id == report.id))
        for item in items:
            db.add(model(report_id=report.id, **item.model_dump(exclude_none=True)))

    await db.commit()
    await db.refresh(report)
    return _report_summary(report)


@router.get("/")
async def list_daily_reports(
    current_user: CurrentUser, db: DB, pages: Pages,
    project_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    query = select(DailyReport)
    if project_id:
        query = query.where(DailyReport.project_id == project_id)
    if status_filter:
        query = query.where(DailyReport.status == status_filter)
    if date_from:
        query = query.where(DailyReport.report_date >= date_from)
    if date_to:
        query = query.where(DailyReport.report_date <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(DailyReport.report_date.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)

    return {"total": total, "page": pages.page, "size": pages.size,
            "items": [_report_summary(r) for r in result.scalars().all()]}


@router.get("/{report_id}")
async def get_daily_report(report_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(DailyReport)
        .options(
            selectinload(DailyReport.activities),
            selectinload(DailyReport.manpower),
            selectinload(DailyReport.equipment_log),
            selectinload(DailyReport.materials_log),
            selectinload(DailyReport.photos),
        )
        .where(DailyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    data = _report_summary(report)
    data["activities"] = [
        {"activity_name": a.activity_name, "work_done": a.work_done,
         "progress_today": float(a.progress_today or 0), "crew_count": a.crew_count}
        for a in report.activities
    ]
    data["manpower"] = [
        {"employee_id": str(m.employee_id) if m.employee_id else None,
         "hours_worked": float(m.hours_worked or 0), "overtime_hours": float(m.overtime_hours or 0)}
        for m in report.manpower
    ]
    data["equipment"] = [
        {"equipment_name": e.equipment_name, "hours_worked": float(e.hours_worked or 0)}
        for e in report.equipment_log
    ]
    data["materials"] = [
        {"material_name": m.material_name, "quantity": float(m.quantity or 0), "unit": m.unit}
        for m in report.materials_log
    ]
    data["photos"] = [{"url": p.file_url, "caption": p.caption} for p in report.photos]
    data["manpower_count"] = sum(1 for _ in report.manpower)
    return data


@router.post("/{report_id}/approve")
async def approve_report(report_id: UUID, body: ApprovalAction, current_user: CurrentUser, db: DB):
    result = await db.execute(select(DailyReport).where(DailyReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted reports can be approved/rejected")

    report.status = "approved" if body.approve else "rejected"
    report.approved_by = current_user.id
    report.approved_at = datetime.now(timezone.utc)
    if not body.approve:
        report.rejection_reason = body.rejection_reason

    await db.commit()
    return {"id": str(report.id), "status": report.status}


@router.post("/{report_id}/photos")
async def add_photo(report_id: UUID, file_url: str, caption: Optional[str], current_user: CurrentUser, db: DB):
    """Attach a photo URL (after upload via /uploads endpoint) to a report."""
    result = await db.execute(select(DailyReport).where(DailyReport.id == report_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Report not found")

    photo = DailyReportPhoto(report_id=report_id, file_url=file_url, caption=caption)
    db.add(photo)
    await db.commit()
    return {"message": "Photo added"}


@router.get("/missing/{project_id}")
async def missing_reports(project_id: UUID, current_user: CurrentUser, db: DB, days_back: int = 7):
    """List dates in the last N days with no submitted report — for reminders."""
    from datetime import timedelta
    today = date.today()
    result = await db.execute(
        select(DailyReport.report_date).where(
            DailyReport.project_id == project_id,
            DailyReport.report_date >= today - timedelta(days=days_back),
        )
    )
    existing_dates = {r[0] for r in result}
    all_dates = {today - timedelta(days=i) for i in range(days_back)}
    missing = sorted(all_dates - existing_dates, reverse=True)
    return {"missing_dates": [d.isoformat() for d in missing]}
