from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

from core.deps import CurrentUser, DB
from models.core import Risk

router = APIRouter()

PROB_SCORE = {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5}
IMPACT_SCORE = {"negligible": 1, "minor": 2, "moderate": 3, "major": 4, "severe": 5}


class RiskCreate(BaseModel):
    project_id: UUID
    risk_number: Optional[str] = None
    title: str
    title_ar: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    probability: str = "medium"
    impact: str = "moderate"
    mitigation_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    owner_id: Optional[UUID] = None
    review_date: Optional[date] = None


class RiskUpdate(BaseModel):
    probability: Optional[str] = None
    impact: Optional[str] = None
    status: Optional[str] = None
    mitigation_plan: Optional[str] = None
    review_date: Optional[date] = None


def _to_dict(r) -> dict:
    score = PROB_SCORE.get(r.probability, 3) * IMPACT_SCORE.get(r.impact, 3)
    return {
        "id": str(r.id),
        "risk_number": r.risk_number,
        "title": r.title,
        "title_ar": r.title_ar,
        "category": r.category,
        "probability": r.probability,
        "impact": r.impact,
        "risk_score": score,
        "risk_level": "critical" if score >= 16 else "high" if score >= 9 else "medium" if score >= 4 else "low",
        "status": r.status,
        "mitigation_plan": r.mitigation_plan,
        "review_date": r.review_date.isoformat() if r.review_date else None,
    }


@router.get("/")
async def list_risks(project_id: UUID, current_user: CurrentUser, db: DB, status_filter: Optional[str] = None):
    query = select(Risk).where(Risk.project_id == project_id)
    if status_filter:
        query = query.where(Risk.status == status_filter)
    result = await db.execute(query.order_by(Risk.created_at.desc()))
    risks = [_to_dict(r) for r in result.scalars().all()]
    return {
        "total": len(risks),
        "open_count": sum(1 for r in risks if r["status"] == "open"),
        "items": sorted(risks, key=lambda x: -x["risk_score"]),
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_risk(body: RiskCreate, current_user: CurrentUser, db: DB):
    risk = Risk(created_by=current_user.id, **body.model_dump(exclude_none=True))
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return _to_dict(risk)


@router.put("/{risk_id}")
async def update_risk(risk_id: UUID, body: RiskUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Risk).where(Risk.id == risk_id))
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(risk, field, value)
    await db.commit()
    await db.refresh(risk)
    return _to_dict(risk)


@router.delete("/{risk_id}", status_code=204)
async def delete_risk(risk_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Risk).where(Risk.id == risk_id))
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    await db.delete(risk)
    await db.commit()


@router.get("/matrix/{project_id}")
async def risk_matrix(project_id: UUID, current_user: CurrentUser, db: DB):
    """5x5 probability/impact matrix counts for visualization."""
    result = await db.execute(
        select(Risk.probability, Risk.impact, func.count())
        .where(Risk.project_id == project_id, Risk.status == "open")
        .group_by(Risk.probability, Risk.impact)
    )
    matrix = {}
    for prob, impact, count in result:
        matrix.setdefault(prob, {})[impact] = count
    return {"matrix": matrix}
