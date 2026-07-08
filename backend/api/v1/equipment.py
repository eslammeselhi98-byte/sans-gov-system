from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.core import Equipment, DailyReportEquipment

router = APIRouter()


class EquipmentCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    category: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    plate_number: Optional[str] = None
    daily_rate: Optional[float] = None


class EquipmentUpdate(BaseModel):
    status: Optional[str] = None
    current_project_id: Optional[UUID] = None
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    notes: Optional[str] = None


def _to_dict(e: Equipment) -> dict:
    return {
        "id": str(e.id), "code": e.code, "name": e.name, "name_ar": e.name_ar,
        "category": e.category, "make": e.make, "model": e.model,
        "status": e.status, "current_project_id": str(e.current_project_id) if e.current_project_id else None,
        "daily_rate": float(e.daily_rate) if e.daily_rate else None,
        "next_maintenance": e.next_maintenance.isoformat() if e.next_maintenance else None,
    }


@router.get("/")
async def list_equipment(
    current_user: CurrentUser, db: DB, pages: Pages,
    status_filter: Optional[str] = None,
    project_id: Optional[UUID] = None,
):
    query = select(Equipment).where(Equipment.company_id == current_user.company_id)
    if status_filter:
        query = query.where(Equipment.status == status_filter)
    if project_id:
        query = query.where(Equipment.current_project_id == project_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    result = await db.execute(query.offset(pages.offset).limit(pages.size))
    return {"total": total, "items": [_to_dict(e) for e in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_equipment(body: EquipmentCreate, current_user: CurrentUser, db: DB):
    eq = Equipment(company_id=current_user.company_id, **body.model_dump(exclude_none=True))
    db.add(eq)
    await db.commit()
    await db.refresh(eq)
    return _to_dict(eq)


@router.put("/{equipment_id}")
async def update_equipment(equipment_id: UUID, body: EquipmentUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Equipment).where(Equipment.id == equipment_id))
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipment not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(eq, field, value)
    await db.commit()
    return _to_dict(eq)


@router.get("/{equipment_id}/utilization")
async def equipment_utilization(equipment_id: UUID, current_user: CurrentUser, db: DB, days: int = 30):
    """Hours worked / utilization over the period, from daily report logs."""
    from datetime import timedelta
    result = await db.execute(
        select(func.sum(DailyReportEquipment.hours_worked), func.count())
        .where(
            DailyReportEquipment.equipment_id == equipment_id,
        )
    )
    row = result.first()
    total_hours = float(row[0] or 0)
    possible_hours = days * 10  # assume 10hr working day
    return {
        "equipment_id": str(equipment_id),
        "total_hours_logged": total_hours,
        "utilization_pct": round(total_hours / possible_hours * 100, 1) if possible_hours else 0,
    }
