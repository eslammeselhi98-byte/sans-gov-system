from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, text
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timezone
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.core import ActualCost, Variation, PaymentCertificate
from models.project import EarnedValueSnapshot, Project

router = APIRouter()


class ActualCostCreate(BaseModel):
    project_id: UUID
    boq_item_id: Optional[UUID] = None
    description: str
    cost_category: str = "other"
    amount: float
    currency: str = "SAR"
    cost_date: date
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None


class VariationCreate(BaseModel):
    project_id: UUID
    variation_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    amount: float = 0
    time_impact_days: int = 0


class VariationAction(BaseModel):
    approve: bool


class PaymentCertCreate(BaseModel):
    project_id: UUID
    cert_number: int
    period_from: date
    period_to: date
    gross_amount: float
    vat_amount: float = 0
    retention_amount: float = 0


# ─── Actual Costs ───────────────────────────────────────────────

@router.get("/actuals")
async def list_actual_costs(
    current_user: CurrentUser, db: DB, pages: Pages,
    project_id: Optional[UUID] = None,
    category: Optional[str] = None,
):
    query = select(ActualCost)
    if project_id:
        query = query.where(ActualCost.project_id == project_id)
    if category:
        query = query.where(ActualCost.cost_category == category)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(ActualCost.cost_date.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)

    return {
        "total": total,
        "items": [
            {
                "id": str(c.id), "description": c.description, "cost_category": c.cost_category,
                "amount": float(c.amount), "cost_date": c.cost_date.isoformat(),
                "vendor": c.vendor, "invoice_number": c.invoice_number,
            }
            for c in result.scalars().all()
        ],
    }


@router.post("/actuals", status_code=201)
async def create_actual_cost(body: ActualCostCreate, current_user: CurrentUser, db: DB):
    cost = ActualCost(entered_by=current_user.id, **body.model_dump(exclude_none=True))
    db.add(cost)
    await db.commit()
    await db.refresh(cost)
    return {"id": str(cost.id), "amount": float(cost.amount)}


@router.get("/summary/{project_id}")
async def cost_summary(project_id: UUID, current_user: CurrentUser, db: DB):
    """Budget vs actual vs committed summary, by category."""
    result = await db.execute(
        select(ActualCost.cost_category, func.sum(ActualCost.amount))
        .where(ActualCost.project_id == project_id)
        .group_by(ActualCost.cost_category)
    )
    by_category = {row[0]: float(row[1]) for row in result}

    total_actual = sum(by_category.values())

    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    contract_value = float(project.contract_value or 0) if project else 0

    return {
        "project_id": str(project_id),
        "contract_value": contract_value,
        "total_actual_cost": total_actual,
        "remaining_budget": contract_value - total_actual,
        "utilization_pct": round(total_actual / contract_value * 100, 2) if contract_value else 0,
        "by_category": by_category,
    }


@router.post("/evm/{project_id}/snapshot")
async def trigger_evm_snapshot(project_id: UUID, current_user: CurrentUser, db: DB):
    """Manually trigger an EVM snapshot calculation (also runs nightly via Celery)."""
    await db.execute(text("SELECT snapshot_earned_value(:pid)"), {"pid": str(project_id)})
    await db.commit()

    result = await db.execute(
        select(EarnedValueSnapshot)
        .where(EarnedValueSnapshot.project_id == project_id)
        .order_by(EarnedValueSnapshot.snapshot_date.desc())
        .limit(1)
    )
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=500, detail="Snapshot failed")

    return {
        "snapshot_date": ev.snapshot_date.isoformat(),
        "spi": float(ev.spi), "cpi": float(ev.cpi),
        "bcws": float(ev.bcws), "bcwp": float(ev.bcwp), "acwp": float(ev.acwp),
        "eac": float(ev.eac), "etc": float(ev.etc),
    }


# ─── Variations ──────────────────────────────────────────────────

@router.get("/variations")
async def list_variations(project_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Variation).where(Variation.project_id == project_id).order_by(Variation.created_at.desc())
    )
    return [
        {
            "id": str(v.id), "variation_number": v.variation_number, "title": v.title,
            "amount": float(v.amount), "time_impact_days": v.time_impact_days, "status": v.status,
        }
        for v in result.scalars().all()
    ]


@router.post("/variations", status_code=201)
async def create_variation(body: VariationCreate, current_user: CurrentUser, db: DB):
    var = Variation(
        submitted_by=current_user.id,
        submitted_date=date.today(),
        **body.model_dump(exclude_none=True),
    )
    db.add(var)
    await db.commit()
    await db.refresh(var)
    return {"id": str(var.id), "status": var.status}


@router.post("/variations/{variation_id}/action")
async def action_variation(variation_id: UUID, body: VariationAction, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Variation).where(Variation.id == variation_id))
    var = result.scalar_one_or_none()
    if not var:
        raise HTTPException(status_code=404, detail="Variation not found")

    var.status = "approved" if body.approve else "rejected"
    var.approved_by = current_user.id
    var.approved_date = date.today()
    await db.commit()
    return {"id": str(var.id), "status": var.status}


# ─── Payment Certificates ────────────────────────────────────────

@router.get("/payment-certificates")
async def list_payment_certs(project_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(PaymentCertificate)
        .where(PaymentCertificate.project_id == project_id)
        .order_by(PaymentCertificate.cert_number)
    )
    return [
        {
            "id": str(c.id), "cert_number": c.cert_number,
            "period_from": c.period_from.isoformat() if c.period_from else None,
            "period_to": c.period_to.isoformat() if c.period_to else None,
            "gross_amount": float(c.gross_amount), "net_amount": float(c.net_amount),
            "status": c.status,
        }
        for c in result.scalars().all()
    ]


@router.post("/payment-certificates", status_code=201)
async def create_payment_cert(body: PaymentCertCreate, current_user: CurrentUser, db: DB):
    net = body.gross_amount + body.vat_amount - body.retention_amount

    # Cumulative from previous certs
    prev = await db.execute(
        select(func.sum(PaymentCertificate.net_amount))
        .where(PaymentCertificate.project_id == body.project_id)
    )
    cumulative = float(prev.scalar() or 0) + net

    cert = PaymentCertificate(
        created_by=current_user.id,
        net_amount=net,
        cumulative_amount=cumulative,
        submitted_date=date.today(),
        **body.model_dump(exclude_none=True),
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return {"id": str(cert.id), "net_amount": net, "cumulative_amount": cumulative}
