from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, time, timezone
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.employee import Employee, Attendance, LeaveRequest, OvertimeRequest

router = APIRouter()


class CheckInRequest(BaseModel):
    employee_id: UUID
    project_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CheckOutRequest(BaseModel):
    employee_id: UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LeaveCreate(BaseModel):
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = None


class OvertimeCreate(BaseModel):
    employee_id: UUID
    project_id: Optional[UUID] = None
    request_date: date
    hours: float
    reason: Optional[str] = None


class ApprovalAction(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None


# ─── Check-in / Check-out ──────────────────────────────────────

@router.post("/check-in", status_code=201)
async def check_in(body: CheckInRequest, current_user: CurrentUser, db: DB):
    today = date.today()
    existing = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == body.employee_id,
            Attendance.report_date == today,
        )
    )
    record = existing.scalar_one_or_none()
    now_str = datetime.now().strftime("%H:%M:%S")

    if record:
        if record.check_in:
            raise HTTPException(status_code=400, detail="Already checked in today")
        record.check_in = now_str
        record.check_in_lat = body.latitude
        record.check_in_lng = body.longitude
    else:
        record = Attendance(
            employee_id=body.employee_id,
            project_id=body.project_id,
            report_date=today,
            check_in=now_str,
            check_in_lat=body.latitude,
            check_in_lng=body.longitude,
            status="present",
        )
        db.add(record)

    await db.commit()
    return {"message": "Checked in", "time": now_str}


@router.post("/check-out")
async def check_out(body: CheckOutRequest, current_user: CurrentUser, db: DB):
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == body.employee_id,
            Attendance.report_date == today,
        )
    )
    record = result.scalar_one_or_none()
    if not record or not record.check_in:
        raise HTTPException(status_code=400, detail="No check-in record found for today")

    now = datetime.now()
    now_str = now.strftime("%H:%M:%S")
    record.check_out = now_str
    record.check_out_lat = body.latitude
    record.check_out_lng = body.longitude

    # Calculate hours worked
    check_in_time = datetime.strptime(record.check_in, "%H:%M:%S")
    check_out_time = datetime.strptime(now_str, "%H:%M:%S")
    delta_hours = (check_out_time - check_in_time).total_seconds() / 3600
    record.hours_worked = round(max(delta_hours, 0), 2)
    record.overtime_hours = round(max(delta_hours - 8, 0), 2)

    await db.commit()
    return {
        "message": "Checked out",
        "time": now_str,
        "hours_worked": float(record.hours_worked),
        "overtime_hours": float(record.overtime_hours),
    }


@router.get("/")
async def list_attendance(
    current_user: CurrentUser, db: DB, pages: Pages,
    employee_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    query = select(Attendance)
    if employee_id:
        query = query.where(Attendance.employee_id == employee_id)
    if project_id:
        query = query.where(Attendance.project_id == project_id)
    if date_from:
        query = query.where(Attendance.report_date >= date_from)
    if date_to:
        query = query.where(Attendance.report_date <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Attendance.report_date.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": total, "page": pages.page, "size": pages.size,
        "items": [
            {
                "id": str(r.id),
                "employee_id": str(r.employee_id),
                "project_id": str(r.project_id) if r.project_id else None,
                "report_date": r.report_date.isoformat(),
                "check_in": r.check_in,
                "check_out": r.check_out,
                "hours_worked": float(r.hours_worked or 0),
                "overtime_hours": float(r.overtime_hours or 0),
                "status": r.status,
            }
            for r in records
        ],
    }


@router.get("/summary/{employee_id}")
async def attendance_summary(employee_id: UUID, current_user: CurrentUser, db: DB, month: Optional[int] = None, year: Optional[int] = None):
    """Monthly attendance summary for an employee."""
    today = date.today()
    month = month or today.month
    year = year or today.year

    result = await db.execute(
        select(
            func.count().label("days_present"),
            func.sum(Attendance.hours_worked).label("total_hours"),
            func.sum(Attendance.overtime_hours).label("total_overtime"),
        ).where(
            Attendance.employee_id == employee_id,
            func.extract("month", Attendance.report_date) == month,
            func.extract("year", Attendance.report_date) == year,
        )
    )
    row = result.first()
    return {
        "employee_id": str(employee_id),
        "month": month,
        "year": year,
        "days_present": row.days_present or 0,
        "total_hours": float(row.total_hours or 0),
        "total_overtime": float(row.total_overtime or 0),
    }


# ─── Leave Requests ─────────────────────────────────────────────

@router.post("/leave", status_code=201)
async def create_leave_request(body: LeaveCreate, current_user: CurrentUser, db: DB):
    days_count = (body.end_date - body.start_date).days + 1
    leave = LeaveRequest(
        employee_id=body.employee_id,
        leave_type=body.leave_type,
        start_date=body.start_date,
        end_date=body.end_date,
        days_count=days_count,
        reason=body.reason,
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return {"id": str(leave.id), "days_count": days_count, "status": "pending"}


@router.get("/leave")
async def list_leave_requests(
    current_user: CurrentUser, db: DB, pages: Pages,
    employee_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
):
    query = select(LeaveRequest)
    if employee_id:
        query = query.where(LeaveRequest.employee_id == employee_id)
    if status_filter:
        query = query.where(LeaveRequest.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(LeaveRequest.created_at.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)

    return {
        "total": total, "page": pages.page, "size": pages.size,
        "items": [
            {
                "id": str(l.id), "employee_id": str(l.employee_id),
                "leave_type": l.leave_type, "start_date": l.start_date.isoformat(),
                "end_date": l.end_date.isoformat(), "days_count": l.days_count,
                "reason": l.reason, "status": l.status,
            }
            for l in result.scalars().all()
        ],
    }


@router.post("/leave/{leave_id}/action")
async def action_leave_request(leave_id: UUID, body: ApprovalAction, current_user: CurrentUser, db: DB):
    result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave.status = "approved" if body.approve else "rejected"
    leave.approved_by = current_user.id
    leave.approved_at = datetime.now(timezone.utc)
    if not body.approve:
        leave.rejection_reason = body.rejection_reason

    await db.commit()
    return {"id": str(leave.id), "status": leave.status}


# ─── Overtime Requests ──────────────────────────────────────────

@router.post("/overtime", status_code=201)
async def create_overtime_request(body: OvertimeCreate, current_user: CurrentUser, db: DB):
    ot = OvertimeRequest(**body.model_dump())
    db.add(ot)
    await db.commit()
    await db.refresh(ot)
    return {"id": str(ot.id), "status": "pending"}


@router.get("/overtime")
async def list_overtime_requests(
    current_user: CurrentUser, db: DB, pages: Pages,
    employee_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
):
    query = select(OvertimeRequest)
    if employee_id:
        query = query.where(OvertimeRequest.employee_id == employee_id)
    if status_filter:
        query = query.where(OvertimeRequest.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(OvertimeRequest.created_at.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)

    return {
        "total": total,
        "items": [
            {
                "id": str(o.id), "employee_id": str(o.employee_id),
                "request_date": o.request_date.isoformat(), "hours": float(o.hours),
                "reason": o.reason, "status": o.status,
            }
            for o in result.scalars().all()
        ],
    }


@router.post("/overtime/{overtime_id}/action")
async def action_overtime_request(overtime_id: UUID, body: ApprovalAction, current_user: CurrentUser, db: DB):
    result = await db.execute(select(OvertimeRequest).where(OvertimeRequest.id == overtime_id))
    ot = result.scalar_one_or_none()
    if not ot:
        raise HTTPException(status_code=404, detail="Overtime request not found")

    ot.status = "approved" if body.approve else "rejected"
    ot.approved_by = current_user.id
    ot.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(ot.id), "status": ot.status}
