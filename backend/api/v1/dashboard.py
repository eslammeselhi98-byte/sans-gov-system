from fastapi import APIRouter
from sqlalchemy import select, func, and_, case
from datetime import date, timedelta
from core.deps import CurrentUser, DB
from models.project import Project, EarnedValueSnapshot, WBSItem
from models.employee import Employee, Attendance
from models.core import DailyReport, ActualCost, Risk, AIRecommendation

router = APIRouter()


@router.get("/executive")
async def executive_dashboard(current_user: CurrentUser, db: DB):
    """
    Main executive dashboard:
    - Portfolio summary
    - Financial KPIs
    - Active alerts
    - AI recommendations count
    """
    company_id = current_user.company_id

    # ── Project counts by status ──────────────────────────────
    proj_stats = await db.execute(
        select(
            Project.status,
            func.count().label("count"),
            func.sum(Project.contract_value).label("total_value"),
        )
        .where(Project.company_id == company_id)
        .group_by(Project.status)
    )
    proj_by_status = {row.status: {"count": row.count, "value": float(row.total_value or 0)}
                      for row in proj_stats}

    total_projects = sum(v["count"] for v in proj_by_status.values())
    active_projects = proj_by_status.get("active", {}).get("count", 0)
    total_portfolio_value = sum(v["value"] for v in proj_by_status.values())

    # ── Active project IDs ────────────────────────────────────
    active_ids_result = await db.execute(
        select(Project.id).where(Project.company_id == company_id, Project.status == "active")
    )
    active_ids = [r[0] for r in active_ids_result]

    # ── Average SPI / CPI from latest EV snapshots ────────────
    ev_stats = {"avg_spi": 1.0, "avg_cpi": 1.0}
    if active_ids:
        # Get latest snapshot per project
        subq = (
            select(
                EarnedValueSnapshot.project_id,
                func.max(EarnedValueSnapshot.snapshot_date).label("max_date")
            )
            .where(EarnedValueSnapshot.project_id.in_(active_ids))
            .group_by(EarnedValueSnapshot.project_id)
            .subquery()
        )
        ev_result = await db.execute(
            select(func.avg(EarnedValueSnapshot.spi), func.avg(EarnedValueSnapshot.cpi))
            .join(subq, and_(
                EarnedValueSnapshot.project_id == subq.c.project_id,
                EarnedValueSnapshot.snapshot_date == subq.c.max_date
            ))
        )
        row = ev_result.first()
        ev_stats = {
            "avg_spi": round(float(row[0] or 1), 3),
            "avg_cpi": round(float(row[1] or 1), 3),
        }

    # ── Total actual cost (all active projects) ───────────────
    cost_result = await db.execute(
        select(func.sum(ActualCost.amount))
        .where(ActualCost.project_id.in_(active_ids) if active_ids else ActualCost.project_id.is_(None))
    )
    total_actual_cost = float(cost_result.scalar() or 0)

    # ── Overdue activities ─────────────────────────────────────
    overdue_result = await db.execute(
        select(func.count()).where(
            WBSItem.project_id.in_(active_ids) if active_ids else WBSItem.project_id.is_(None),
            WBSItem.is_activity == True,
            WBSItem.actual_finish.is_(None),
            WBSItem.planned_finish < date.today(),
        )
    )
    overdue_activities = int(overdue_result.scalar() or 0)

    # ── Open risks ────────────────────────────────────────────
    risk_result = await db.execute(
        select(func.count()).where(
            Risk.project_id.in_(active_ids) if active_ids else Risk.project_id.is_(None),
            Risk.status == "open"
        )
    )
    open_risks = int(risk_result.scalar() or 0)

    # ── Active employees ──────────────────────────────────────
    emp_result = await db.execute(
        select(func.count()).where(
            Employee.company_id == company_id,
            Employee.is_active == True
        )
    )
    active_employees = int(emp_result.scalar() or 0)

    # ── Today's attendance ────────────────────────────────────
    att_result = await db.execute(
        select(func.count()).where(
            Attendance.report_date == date.today()
        )
    )
    today_attendance = int(att_result.scalar() or 0)

    # ── Pending reports (not submitted) ───────────────────────
    pending_reports = 0
    if active_ids:
        yesterday = date.today() - timedelta(days=1)
        pr_result = await db.execute(
            select(func.count()).where(
                DailyReport.project_id.in_(active_ids),
                DailyReport.report_date == yesterday,
                DailyReport.status.in_(["draft", "submitted"])
            )
        )
        pending_reports = int(pr_result.scalar() or 0)

    # ── Unread AI recommendations ─────────────────────────────
    ai_result = await db.execute(
        select(func.count()).where(
            AIRecommendation.project_id.in_(active_ids) if active_ids else AIRecommendation.project_id.is_(None),
            AIRecommendation.acknowledged == False,
            AIRecommendation.priority.in_(["critical", "high"])
        )
    )
    urgent_recommendations = int(ai_result.scalar() or 0)

    # ── Expiring documents (employees) ───────────────────────
    exp_result = await db.execute(
        select(func.count()).where(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.iqama_expiry <= date.today() + timedelta(days=30),
        )
    )
    expiring_documents = int(exp_result.scalar() or 0)

    return {
        "portfolio": {
            "total_projects": total_projects,
            "active": active_projects,
            "planning": proj_by_status.get("planning", {}).get("count", 0),
            "on_hold": proj_by_status.get("on_hold", {}).get("count", 0),
            "completed": proj_by_status.get("completed", {}).get("count", 0),
            "total_value_sar": total_portfolio_value,
        },
        "performance": {
            "avg_spi": ev_stats["avg_spi"],
            "avg_cpi": ev_stats["avg_cpi"],
            "total_actual_cost": total_actual_cost,
            "overdue_activities": overdue_activities,
        },
        "workforce": {
            "active_employees": active_employees,
            "today_attendance": today_attendance,
            "attendance_rate": round(today_attendance / active_employees * 100, 1) if active_employees else 0,
            "expiring_iqama_30d": expiring_documents,
        },
        "alerts": {
            "open_risks": open_risks,
            "pending_reports": pending_reports,
            "urgent_ai_recommendations": urgent_recommendations,
        },
    }


@router.get("/projects/{project_id}/scurve")
async def get_scurve(project_id: str, current_user: CurrentUser, db: DB):
    """Return S-curve data (planned vs actual progress over time)."""
    from uuid import UUID
    pid = UUID(project_id)

    result = await db.execute(
        select(EarnedValueSnapshot)
        .where(EarnedValueSnapshot.project_id == pid)
        .order_by(EarnedValueSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()

    # Get project BAC
    proj_result = await db.execute(select(Project).where(Project.id == pid))
    project = proj_result.scalar_one_or_none()
    bac = float(project.contract_value or 0) if project else 0

    data = []
    for s in snapshots:
        data.append({
            "date": s.snapshot_date.isoformat(),
            "planned": round(float(s.bcws or 0) / bac * 100, 2) if bac else 0,
            "actual": round(float(s.percent_complete or 0), 2),
            "spi": round(float(s.spi or 1), 3),
            "cpi": round(float(s.cpi or 1), 3),
            "bcws": float(s.bcws or 0),
            "bcwp": float(s.bcwp or 0),
            "acwp": float(s.acwp or 0),
        })

    return {"project_id": project_id, "bac": bac, "data": data}


@router.get("/projects/{project_id}/milestones")
async def get_milestone_status(project_id: str, current_user: CurrentUser, db: DB):
    """Return milestone schedule adherence."""
    from uuid import UUID
    from models.project import Milestone
    pid = UUID(project_id)

    result = await db.execute(
        select(Milestone)
        .where(Milestone.project_id == pid)
        .order_by(Milestone.planned_date)
    )
    milestones = result.scalars().all()

    today = date.today()
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "name_ar": m.name_ar,
            "planned_date": m.planned_date.isoformat() if m.planned_date else None,
            "actual_date": m.actual_date.isoformat() if m.actual_date else None,
            "status": m.status,
            "is_overdue": m.planned_date and m.planned_date < today and not m.actual_date,
            "variance_days": (
                (m.actual_date - m.planned_date).days
                if m.actual_date and m.planned_date else None
            ),
        }
        for m in milestones
    ]


@router.get("/alerts")
async def get_alerts(current_user: CurrentUser, db: DB):
    """Return system-wide alerts for the current user's company."""
    company_id = current_user.company_id
    today = date.today()
    alerts = []

    # Overdue activities
    active_ids_result = await db.execute(
        select(Project.id).where(Project.company_id == company_id, Project.status == "active")
    )
    active_ids = [r[0] for r in active_ids_result]

    if active_ids:
        overdue = await db.execute(
            select(WBSItem.name, WBSItem.planned_finish, Project.name.label("proj"))
            .join(Project, WBSItem.project_id == Project.id)
            .where(
                WBSItem.project_id.in_(active_ids),
                WBSItem.is_activity == True,
                WBSItem.actual_finish.is_(None),
                WBSItem.planned_finish < today,
            ).limit(10)
        )
        for row in overdue:
            alerts.append({
                "type": "overdue_activity",
                "severity": "high",
                "message": f"Overdue: {row.name} ({row.proj})",
                "date": row.planned_finish.isoformat() if row.planned_finish else None,
            })

    # Expiring employee documents
    exp_emps = await db.execute(
        select(Employee.full_name, Employee.iqama_expiry)
        .where(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.iqama_expiry <= today + timedelta(days=30),
            Employee.iqama_expiry >= today,
        ).limit(10)
    )
    for row in exp_emps:
        days_left = (row.iqama_expiry - today).days
        alerts.append({
            "type": "iqama_expiry",
            "severity": "critical" if days_left <= 7 else "warning",
            "message": f"Iqama expiring in {days_left} days: {row.full_name}",
            "date": row.iqama_expiry.isoformat(),
        })

    # High-priority AI recommendations
    if active_ids:
        ai_recs = await db.execute(
            select(AIRecommendation)
            .where(
                AIRecommendation.project_id.in_(active_ids),
                AIRecommendation.acknowledged == False,
                AIRecommendation.priority == "critical",
            ).limit(5)
        )
        for rec in ai_recs.scalars():
            alerts.append({
                "type": "ai_recommendation",
                "severity": "critical",
                "message": rec.title or rec.recommendation[:100],
                "date": rec.created_at.isoformat() if rec.created_at else None,
            })

    return {"count": len(alerts), "alerts": sorted(alerts, key=lambda x: x["severity"])}
