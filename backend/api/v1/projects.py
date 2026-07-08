from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID

from core.deps import CurrentUser, DB, Pages, CompanyID
from models.project import Project, ProjectMember, EarnedValueSnapshot
from models.user import User

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    client: Optional[str] = None
    client_ar: Optional[str] = None
    contract_number: Optional[str] = None
    tender_number: Optional[str] = None
    project_type: str = "civil"
    start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    contract_value: Optional[float] = None
    currency: str = "SAR"
    vat_rate: float = 15.0
    retention_rate: float = 10.0
    location: Optional[str] = None
    location_ar: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    project_manager_id: Optional[UUID] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    client: Optional[str] = None
    contract_number: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    contract_value: Optional[float] = None
    location: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    project_manager_id: Optional[UUID] = None
    data_date: Optional[date] = None
    description: Optional[str] = None


class MemberAdd(BaseModel):
    user_id: UUID
    role_in_project: Optional[str] = None
    can_submit_reports: bool = False
    can_approve_reports: bool = False
    can_edit_schedule: bool = False


# ─── Routes ───────────────────────────────────────────────────

@router.get("/")
async def list_projects(
    current_user: CurrentUser,
    db: DB,
    pages: Pages,
    status: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all projects for the company."""
    query = select(Project).where(Project.company_id == current_user.company_id)

    if status:
        query = query.where(Project.status == status)
    if region:
        query = query.where(Project.region == region)
    if search:
        query = query.where(
            Project.name.ilike(f"%{search}%") | Project.name_ar.ilike(f"%{search}%") |
            Project.code.ilike(f"%{search}%") | Project.contract_number.ilike(f"%{search}%")
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    query = query.offset(pages.offset).limit(pages.size).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    return {
        "total": total,
        "page": pages.page,
        "size": pages.size,
        "items": [_project_to_dict(p) for p in projects],
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, current_user: CurrentUser, db: DB):
    """Create a new project."""
    # Check code uniqueness
    existing = await db.execute(
        select(Project).where(
            Project.company_id == current_user.company_id,
            Project.code == body.code
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project code '{body.code}' already exists")

    project = Project(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(exclude_none=True)
    )
    db.add(project)

    # Auto-add creator as member
    await db.flush()
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role_in_project="Project Creator",
        can_submit_reports=True,
        can_approve_reports=True,
        can_edit_schedule=True,
    )
    db.add(member)
    await db.commit()
    await db.refresh(project)
    return _project_to_dict(project)


@router.get("/{project_id}")
async def get_project(project_id: UUID, current_user: CurrentUser, db: DB):
    """Get a single project with full details."""
    project = await _get_project_or_404(project_id, current_user, db)

    # Latest EV snapshot
    ev_result = await db.execute(
        select(EarnedValueSnapshot)
        .where(EarnedValueSnapshot.project_id == project_id)
        .order_by(EarnedValueSnapshot.snapshot_date.desc())
        .limit(1)
    )
    ev = ev_result.scalar_one_or_none()

    data = _project_to_dict(project)
    if ev:
        data["earned_value"] = {
            "date": ev.snapshot_date.isoformat(),
            "spi": float(ev.spi or 1),
            "cpi": float(ev.cpi or 1),
            "bcws": float(ev.bcws or 0),
            "bcwp": float(ev.bcwp or 0),
            "acwp": float(ev.acwp or 0),
            "bac": float(ev.bac or 0),
            "eac": float(ev.eac or 0),
            "percent_complete": float(ev.percent_complete or 0),
        }

    return data


@router.put("/{project_id}")
async def update_project(project_id: UUID, body: ProjectUpdate, current_user: CurrentUser, db: DB):
    """Update project details."""
    project = await _get_project_or_404(project_id, current_user, db)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return _project_to_dict(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, current_user: CurrentUser, db: DB):
    """Delete a project (admin only)."""
    if not current_user.role or not current_user.role.permissions.get("all"):
        raise HTTPException(status_code=403, detail="Only admins can delete projects")
    project = await _get_project_or_404(project_id, current_user, db)
    await db.delete(project)
    await db.commit()


@router.get("/{project_id}/members")
async def get_members(project_id: UUID, current_user: CurrentUser, db: DB):
    """List project members."""
    await _get_project_or_404(project_id, current_user, db)
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
    )
    rows = result.all()
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "full_name": u.full_name,
            "full_name_ar": u.full_name_ar,
            "email": u.email,
            "role_in_project": m.role_in_project,
            "can_submit_reports": m.can_submit_reports,
            "can_approve_reports": m.can_approve_reports,
            "can_edit_schedule": m.can_edit_schedule,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m, u in rows
    ]


@router.post("/{project_id}/members", status_code=201)
async def add_member(project_id: UUID, body: MemberAdd, current_user: CurrentUser, db: DB):
    """Add a user to a project."""
    await _get_project_or_404(project_id, current_user, db)

    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == body.user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    member = ProjectMember(project_id=project_id, **body.model_dump())
    db.add(member)
    await db.commit()
    return {"message": "Member added successfully"}


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: UUID, user_id: UUID, current_user: CurrentUser, db: DB):
    """Remove a user from a project."""
    await _get_project_or_404(project_id, current_user, db)
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()


@router.get("/{project_id}/stats")
async def get_project_stats(project_id: UUID, current_user: CurrentUser, db: DB):
    """Get project KPIs and statistics summary."""
    from models.core import DailyReport, ActualCost, Risk
    from models.project import WBSItem

    await _get_project_or_404(project_id, current_user, db)

    # Activity stats
    act_result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(WBSItem.is_critical).label("critical"),
            func.avg(WBSItem.percent_complete).label("avg_progress"),
            func.count().filter(WBSItem.actual_finish == None, WBSItem.planned_finish < date.today()).label("overdue"),
        ).where(WBSItem.project_id == project_id, WBSItem.is_activity == True)
    )
    act = act_result.first()

    # Cost stats
    cost_result = await db.execute(
        select(func.sum(ActualCost.amount)).where(ActualCost.project_id == project_id)
    )
    total_cost = cost_result.scalar() or 0

    # Open risks
    risk_result = await db.execute(
        select(func.count()).where(Risk.project_id == project_id, Risk.status == "open")
    )
    open_risks = risk_result.scalar() or 0

    # Recent reports
    report_result = await db.execute(
        select(func.count()).where(
            DailyReport.project_id == project_id,
            DailyReport.status == "submitted"
        )
    )
    total_reports = report_result.scalar() or 0

    return {
        "activities": {
            "total": act.total or 0,
            "critical": act.critical or 0,
            "overdue": act.overdue or 0,
            "avg_progress": round(float(act.avg_progress or 0), 2),
        },
        "cost": {
            "total_actual": float(total_cost),
        },
        "risks": {"open": open_risks},
        "reports": {"total_submitted": total_reports},
    }


# ─── Helpers ──────────────────────────────────────────────────

async def _get_project_or_404(project_id: UUID, current_user, db) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _project_to_dict(p: Project) -> dict:
    return {
        "id": str(p.id),
        "code": p.code,
        "name": p.name,
        "name_ar": p.name_ar,
        "client": p.client,
        "client_ar": p.client_ar,
        "contract_number": p.contract_number,
        "tender_number": p.tender_number,
        "project_type": p.project_type,
        "status": p.status,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "planned_end_date": p.planned_end_date.isoformat() if p.planned_end_date else None,
        "actual_end_date": p.actual_end_date.isoformat() if p.actual_end_date else None,
        "contract_value": float(p.contract_value) if p.contract_value else None,
        "currency": p.currency,
        "vat_rate": float(p.vat_rate) if p.vat_rate else 15.0,
        "location": p.location,
        "location_ar": p.location_ar,
        "city": p.city,
        "region": p.region,
        "latitude": float(p.latitude) if p.latitude else None,
        "longitude": float(p.longitude) if p.longitude else None,
        "data_date": p.data_date.isoformat() if p.data_date else None,
        "days_remaining": (p.planned_end_date - date.today()).days if p.planned_end_date else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
