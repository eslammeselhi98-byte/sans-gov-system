from fastapi import APIRouter, HTTPException, status, UploadFile
from sqlalchemy import select, func, text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID
import io

from core.deps import CurrentUser, DB
from models.project import WBSItem, ActivityRelationship, ProgressUpdate, Calendar

router = APIRouter()


class WBSItemCreate(BaseModel):
    project_id: UUID
    parent_id: Optional[UUID] = None
    code: Optional[str] = None
    name: str
    name_ar: Optional[str] = None
    level: int = 1
    is_activity: bool = True
    activity_type: str = "task"
    planned_start: Optional[date] = None
    planned_finish: Optional[date] = None
    planned_duration: int = 0
    weight: float = 0
    budgeted_cost: float = 0


class ProgressUpdateCreate(BaseModel):
    activity_id: UUID
    project_id: UUID
    report_date: date
    percent_complete: float
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    notes: Optional[str] = None


class RelationshipCreate(BaseModel):
    project_id: UUID
    predecessor_id: UUID
    successor_id: UUID
    rel_type: str = "FS"
    lag: int = 0


def _wbs_to_dict(w: WBSItem) -> dict:
    return {
        "id": str(w.id),
        "parent_id": str(w.parent_id) if w.parent_id else None,
        "code": w.code,
        "name": w.name,
        "name_ar": w.name_ar,
        "level": w.level,
        "is_activity": w.is_activity,
        "activity_type": w.activity_type,
        "planned_start": w.planned_start.isoformat() if w.planned_start else None,
        "planned_finish": w.planned_finish.isoformat() if w.planned_finish else None,
        "actual_start": w.actual_start.isoformat() if w.actual_start else None,
        "actual_finish": w.actual_finish.isoformat() if w.actual_finish else None,
        "percent_complete": float(w.percent_complete or 0),
        "total_float": w.total_float,
        "is_critical": w.is_critical,
        "weight": float(w.weight or 0),
        "budgeted_cost": float(w.budgeted_cost or 0),
    }


@router.get("/")
async def list_wbs(project_id: UUID, current_user: CurrentUser, db: DB):
    """Return the full WBS/schedule tree for a project."""
    result = await db.execute(
        select(WBSItem)
        .where(WBSItem.project_id == project_id)
        .order_by(WBSItem.sort_order, WBSItem.planned_start)
    )
    items = result.scalars().all()
    return {"project_id": str(project_id), "count": len(items), "items": [_wbs_to_dict(i) for i in items]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_wbs_item(body: WBSItemCreate, current_user: CurrentUser, db: DB):
    item = WBSItem(**body.model_dump(exclude_none=True))

    if item.planned_start and item.planned_finish:
        item.planned_duration = (item.planned_finish - item.planned_start).days

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _wbs_to_dict(item)


@router.put("/{item_id}")
async def update_wbs_item(item_id: UUID, body: dict, current_user: CurrentUser, db: DB):
    result = await db.execute(select(WBSItem).where(WBSItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")

    for field, value in body.items():
        if hasattr(item, field):
            setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return _wbs_to_dict(item)


@router.delete("/{item_id}", status_code=204)
async def delete_wbs_item(item_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(WBSItem).where(WBSItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")
    await db.delete(item)
    await db.commit()


@router.post("/relationships", status_code=201)
async def create_relationship(body: RelationshipCreate, current_user: CurrentUser, db: DB):
    rel = ActivityRelationship(**body.model_dump())
    db.add(rel)
    await db.commit()
    return {"message": "Relationship created"}


@router.get("/relationships")
async def list_relationships(project_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ActivityRelationship).where(ActivityRelationship.project_id == project_id)
    )
    return [
        {
            "predecessor_id": str(r.predecessor_id), "successor_id": str(r.successor_id),
            "rel_type": r.rel_type, "lag": r.lag,
        }
        for r in result.scalars().all()
    ]


@router.post("/progress", status_code=201)
async def record_progress(body: ProgressUpdateCreate, current_user: CurrentUser, db: DB):
    """Record a progress update and sync it onto the WBS item itself."""
    update = ProgressUpdate(updated_by=current_user.id, **body.model_dump(exclude_none=True))
    db.add(update)

    result = await db.execute(select(WBSItem).where(WBSItem.id == body.activity_id))
    activity = result.scalar_one_or_none()
    if activity:
        activity.percent_complete = body.percent_complete
        if body.actual_start and not activity.actual_start:
            activity.actual_start = body.actual_start
        if body.actual_finish:
            activity.actual_finish = body.actual_finish
            activity.percent_complete = 100

    await db.commit()

    # Recalculate project rollup progress
    await db.execute(text("SELECT calculate_project_progress(:pid)"), {"pid": str(body.project_id)})
    await db.commit()

    return {"message": "Progress recorded", "percent_complete": body.percent_complete}


@router.get("/critical-path")
async def get_critical_path(project_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(WBSItem)
        .where(WBSItem.project_id == project_id, WBSItem.is_critical == True, WBSItem.is_activity == True)
        .order_by(WBSItem.planned_finish)
    )
    return [_wbs_to_dict(i) for i in result.scalars().all()]


@router.post("/import-xer")
async def import_primavera_xer(project_id: UUID, file: UploadFile, current_user: CurrentUser, db: DB):
    """
    Import activities and relationships from a Primavera P6 .xer file.
    Maps TASK and TASKPRED tables into wbs_items / activity_relationships.
    """
    if not file.filename.endswith(".xer"):
        raise HTTPException(status_code=400, detail="File must be a .xer export from Primavera P6")

    try:
        from xerparser import Xer
    except ImportError:
        raise HTTPException(status_code=500, detail="xerparser package not installed on server")

    contents = await file.read()
    try:
        xer = Xer(contents.decode("utf-8", errors="ignore"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse XER file: {e}")

    created_activities = 0
    created_relationships = 0
    id_map = {}  # xer task_id -> our UUID

    for task in xer.tasks:
        item = WBSItem(
            project_id=project_id,
            external_id=task.task_id,
            code=task.task_code,
            name=task.task_name or task.task_code,
            is_activity=True,
            activity_type="milestone" if "Milestone" in str(task.task_type) else "task",
            planned_start=task.target_start_date.date() if task.target_start_date else None,
            planned_finish=task.target_end_date.date() if task.target_end_date else None,
            actual_start=task.act_start_date.date() if task.act_start_date else None,
            actual_finish=task.act_end_date.date() if task.act_end_date else None,
            total_float=int(task.total_float_hr_cnt) if task.total_float_hr_cnt else 0,
            is_critical=(task.total_float_hr_cnt is not None and float(task.total_float_hr_cnt) <= 0),
            percent_complete=float(task.phys_complete_pct or 0),
        )
        db.add(item)
        await db.flush()
        id_map[task.task_id] = item.id
        created_activities += 1

    for rel in xer.relationships:
        pred_id = id_map.get(rel.pred_task_id)
        succ_id = id_map.get(rel.task_id)
        if pred_id and succ_id:
            db.add(ActivityRelationship(
                project_id=project_id,
                predecessor_id=pred_id,
                successor_id=succ_id,
                rel_type=str(rel.pred_type)[-2:] if rel.pred_type else "FS",
                lag=int(rel.lag_hr_cnt / 8) if rel.lag_hr_cnt else 0,
            ))
            created_relationships += 1

    await db.commit()
    return {
        "activities_imported": created_activities,
        "relationships_imported": created_relationships,
    }
