from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.core import Material

router = APIRouter()


class MaterialCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    min_stock: float = 0
    unit_cost: float = 0
    supplier: Optional[str] = None


class ReceiptItem(BaseModel):
    material_id: UUID
    quantity: float
    unit_cost: float = 0


class ReceiptCreate(BaseModel):
    project_id: UUID
    delivery_note: Optional[str] = None
    supplier: Optional[str] = None
    items: List[ReceiptItem]


class IssueItem(BaseModel):
    material_id: UUID
    quantity: float


class IssueCreate(BaseModel):
    project_id: UUID
    activity_id: Optional[UUID] = None
    items: List[IssueItem]


def _to_dict(m: Material) -> dict:
    return {
        "id": str(m.id), "code": m.code, "name": m.name, "name_ar": m.name_ar,
        "category": m.category, "unit": m.unit,
        "current_stock": float(m.current_stock or 0), "min_stock": float(m.min_stock or 0),
        "unit_cost": float(m.unit_cost or 0),
        "below_minimum": float(m.current_stock or 0) < float(m.min_stock or 0),
    }


@router.get("/")
async def list_materials(current_user: CurrentUser, db: DB, pages: Pages, low_stock_only: bool = False):
    query = select(Material).where(Material.company_id == current_user.company_id)
    result = await db.execute(query.offset(pages.offset).limit(pages.size))
    materials = [_to_dict(m) for m in result.scalars().all()]
    if low_stock_only:
        materials = [m for m in materials if m["below_minimum"]]
    return {"total": len(materials), "items": materials}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_material(body: MaterialCreate, current_user: CurrentUser, db: DB):
    mat = Material(company_id=current_user.company_id, **body.model_dump(exclude_none=True))
    db.add(mat)
    await db.commit()
    await db.refresh(mat)
    return _to_dict(mat)


@router.post("/receipts", status_code=201)
async def create_receipt(body: ReceiptCreate, current_user: CurrentUser, db: DB):
    """Record material receipt — triggers stock increase via DB trigger.
    Uses raw SQL since receipt tables aren't yet modeled in SQLAlchemy ORM (schema.sql has them)."""
    from sqlalchemy import text as sql_text
    import uuid

    receipt_id = str(uuid.uuid4())
    await db.execute(
        sql_text("""
            INSERT INTO material_receipts (id, project_id, received_by, receipt_date, delivery_note, supplier)
            VALUES (:id, :pid, :uid, :rdate, :note, :supplier)
        """),
        {"id": receipt_id, "pid": str(body.project_id), "uid": str(current_user.id),
         "rdate": date.today(), "note": body.delivery_note, "supplier": body.supplier}
    )

    for item in body.items:
        await db.execute(
            sql_text("""
                INSERT INTO material_receipt_items (id, receipt_id, material_id, quantity, unit_cost)
                VALUES (:id, :rid, :mid, :qty, :cost)
            """),
            {"id": str(uuid.uuid4()), "rid": receipt_id, "mid": str(item.material_id),
             "qty": item.quantity, "cost": item.unit_cost}
        )

    await db.commit()
    return {"receipt_id": receipt_id, "items_received": len(body.items)}


@router.post("/issues", status_code=201)
async def create_issue(body: IssueCreate, current_user: CurrentUser, db: DB):
    """Record material issue to site — triggers stock decrease via DB trigger."""
    from sqlalchemy import text as sql_text
    import uuid

    issue_id = str(uuid.uuid4())
    await db.execute(
        sql_text("""
            INSERT INTO material_issues (id, project_id, activity_id, issued_by, issue_date)
            VALUES (:id, :pid, :aid, :uid, :idate)
        """),
        {"id": issue_id, "pid": str(body.project_id),
         "aid": str(body.activity_id) if body.activity_id else None,
         "uid": str(current_user.id), "idate": date.today()}
    )

    for item in body.items:
        # Check stock availability
        stock_check = await db.execute(
            select(Material.current_stock).where(Material.id == item.material_id)
        )
        current_stock = stock_check.scalar() or 0
        if current_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for material {item.material_id}: have {current_stock}, need {item.quantity}"
            )

        await db.execute(
            sql_text("""
                INSERT INTO material_issue_items (id, issue_id, material_id, quantity)
                VALUES (:id, :iid, :mid, :qty)
            """),
            {"id": str(uuid.uuid4()), "iid": issue_id, "mid": str(item.material_id), "qty": item.quantity}
        )

    await db.commit()
    return {"issue_id": issue_id, "items_issued": len(body.items)}


@router.get("/low-stock")
async def low_stock_alert(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Material).where(
            Material.company_id == current_user.company_id,
            Material.current_stock < Material.min_stock,
        )
    )
    return [_to_dict(m) for m in result.scalars().all()]
