from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.employee import Employee, Department, Position

router = APIRouter()


class EmployeeCreate(BaseModel):
    employee_number: str
    full_name: str
    full_name_ar: Optional[str] = None
    nationality: Optional[str] = None
    id_number: Optional[str] = None
    passport_number: Optional[str] = None
    position_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    current_project_id: Optional[UUID] = None
    hire_date: Optional[date] = None
    contract_type: str = "permanent"
    basic_salary: Optional[float] = None
    housing_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    iqama_expiry: Optional[date] = None
    passport_expiry: Optional[date] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    position_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    current_project_id: Optional[UUID] = None
    basic_salary: Optional[float] = None
    iqama_expiry: Optional[date] = None
    passport_expiry: Optional[date] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


def _to_dict(e: Employee) -> dict:
    return {
        "id": str(e.id),
        "employee_number": e.employee_number,
        "full_name": e.full_name,
        "full_name_ar": e.full_name_ar,
        "nationality": e.nationality,
        "id_number": e.id_number,
        "position_id": str(e.position_id) if e.position_id else None,
        "department_id": str(e.department_id) if e.department_id else None,
        "current_project_id": str(e.current_project_id) if e.current_project_id else None,
        "hire_date": e.hire_date.isoformat() if e.hire_date else None,
        "contract_type": e.contract_type,
        "basic_salary": float(e.basic_salary) if e.basic_salary else None,
        "iqama_expiry": e.iqama_expiry.isoformat() if e.iqama_expiry else None,
        "passport_expiry": e.passport_expiry.isoformat() if e.passport_expiry else None,
        "phone": e.phone,
        "is_active": e.is_active,
        "iqama_status": (
            "expired" if e.iqama_expiry and e.iqama_expiry < date.today()
            else "expiring_soon" if e.iqama_expiry and (e.iqama_expiry - date.today()).days <= 30
            else "valid" if e.iqama_expiry else None
        ),
    }


@router.get("/")
async def list_employees(
    current_user: CurrentUser, db: DB, pages: Pages,
    department_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
):
    query = select(Employee).where(Employee.company_id == current_user.company_id)
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if project_id:
        query = query.where(Employee.current_project_id == project_id)
    if is_active is not None:
        query = query.where(Employee.is_active == is_active)
    if search:
        query = query.where(or_(
            Employee.full_name.ilike(f"%{search}%"),
            Employee.full_name_ar.ilike(f"%{search}%"),
            Employee.employee_number.ilike(f"%{search}%"),
        ))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.offset(pages.offset).limit(pages.size).order_by(Employee.full_name)
    result = await db.execute(query)
    employees = result.scalars().all()

    return {"total": total, "page": pages.page, "size": pages.size,
            "items": [_to_dict(e) for e in employees]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_employee(body: EmployeeCreate, current_user: CurrentUser, db: DB):
    existing = await db.execute(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.employee_number == body.employee_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee number already exists")

    emp = Employee(company_id=current_user.company_id, **body.model_dump(exclude_none=True))
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return _to_dict(emp)


@router.get("/{employee_id}")
async def get_employee(employee_id: UUID, current_user: CurrentUser, db: DB):
    emp = await _get_or_404(employee_id, current_user, db)
    data = _to_dict(emp)

    # Department / position names
    if emp.department_id:
        dept = await db.execute(select(Department).where(Department.id == emp.department_id))
        d = dept.scalar_one_or_none()
        if d:
            data["department_name"] = d.name
            data["department_name_ar"] = d.name_ar
    if emp.position_id:
        pos = await db.execute(select(Position).where(Position.id == emp.position_id))
        p = pos.scalar_one_or_none()
        if p:
            data["position_name"] = p.name
            data["position_name_ar"] = p.name_ar

    return data


@router.put("/{employee_id}")
async def update_employee(employee_id: UUID, body: EmployeeUpdate, current_user: CurrentUser, db: DB):
    emp = await _get_or_404(employee_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(emp, field, value)
    await db.commit()
    await db.refresh(emp)
    return _to_dict(emp)


@router.delete("/{employee_id}", status_code=204)
async def deactivate_employee(employee_id: UUID, current_user: CurrentUser, db: DB):
    """Soft-delete: mark inactive rather than hard delete (preserves attendance/payroll history)."""
    emp = await _get_or_404(employee_id, current_user, db)
    emp.is_active = False
    await db.commit()


@router.get("/expiring/documents")
async def expiring_documents(current_user: CurrentUser, db: DB, days: int = 30):
    """List employees with Iqama/passport expiring within N days."""
    from datetime import timedelta
    threshold = date.today() + timedelta(days=days)
    result = await db.execute(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.is_active == True,
            or_(
                Employee.iqama_expiry <= threshold,
                Employee.passport_expiry <= threshold,
            )
        ).order_by(Employee.iqama_expiry)
    )
    return [_to_dict(e) for e in result.scalars().all()]


async def _get_or_404(employee_id: UUID, current_user, db) -> Employee:
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == current_user.company_id
        )
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


# ─── Departments & Positions (lightweight, shared module) ────

@router.get("/departments/list")
async def list_departments(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Department).where(Department.company_id == current_user.company_id)
    )
    return [
        {"id": str(d.id), "name": d.name, "name_ar": d.name_ar, "code": d.code}
        for d in result.scalars().all()
    ]


@router.get("/positions/list")
async def list_positions(current_user: CurrentUser, db: DB, department_id: Optional[UUID] = None):
    query = select(Position).where(Position.company_id == current_user.company_id)
    if department_id:
        query = query.where(Position.department_id == department_id)
    result = await db.execute(query)
    return [
        {"id": str(p.id), "name": p.name, "name_ar": p.name_ar, "code": p.code, "grade": p.grade}
        for p in result.scalars().all()
    ]
