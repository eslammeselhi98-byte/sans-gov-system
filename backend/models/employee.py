import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey,
    Integer, Numeric, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    code = Column(String(20))
    manager_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    positions = relationship("Position", back_populates="department")
    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"))
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    code = Column(String(50))
    grade = Column(String(20))
    basic_salary = Column(Numeric(12, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department", back_populates="positions")
    employees = relationship("Employee", back_populates="position")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    employee_number = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    full_name_ar = Column(String(255))
    nationality = Column(String(100))
    id_number = Column(String(50))
    passport_number = Column(String(50))
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="SET NULL"))
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"))
    manager_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    current_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    hire_date = Column(Date)
    contract_type = Column(String(50), default="permanent")
    contract_end_date = Column(Date)
    basic_salary = Column(Numeric(12, 2))
    housing_allowance = Column(Numeric(12, 2))
    transport_allowance = Column(Numeric(12, 2))
    other_allowances = Column(Numeric(12, 2))
    currency = Column(String(3), default="SAR")
    iqama_expiry = Column(Date)
    passport_expiry = Column(Date)
    medical_expiry = Column(Date)
    safety_cert_expiry = Column(Date)
    phone = Column(String(30))
    emergency_contact = Column(String(255))
    emergency_phone = Column(String(30))
    photo_url = Column(String(500))
    blood_type = Column(String(5))
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="employees")
    user = relationship("User")
    position = relationship("Position", back_populates="employees")
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    current_project = relationship("Project")
    subordinates = relationship("Employee", foreign_keys=[manager_id])
    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    overtime_requests = relationship("OvertimeRequest", back_populates="employee", cascade="all, delete-orphan")
    performance_reviews = relationship("PerformanceReview", back_populates="employee", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    report_date = Column(Date, nullable=False)
    check_in = Column(String(8))  # TIME stored as string HH:MM:SS
    check_out = Column(String(8))
    hours_worked = Column(Numeric(5, 2), default=0)
    overtime_hours = Column(Numeric(5, 2), default=0)
    status = Column(String(20), default="present")
    check_in_lat = Column(Numeric(10, 7))
    check_in_lng = Column(Numeric(10, 7))
    check_out_lat = Column(Numeric(10, 7))
    check_out_lng = Column(Numeric(10, 7))
    notes = Column(Text)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="attendance_records")
    project = relationship("Project")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type = Column(String(30), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Integer)
    reason = Column(Text)
    status = Column(String(20), default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="leave_requests")


class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    request_date = Column(Date, nullable=False)
    hours = Column(Numeric(4, 2), nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="overtime_requests")


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    period_from = Column(Date)
    period_to = Column(Date)
    attendance_score = Column(Numeric(4, 2))
    quality_score = Column(Numeric(4, 2))
    productivity_score = Column(Numeric(4, 2))
    teamwork_score = Column(Numeric(4, 2))
    overall_score = Column(Numeric(4, 2))
    comments = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="performance_reviews")
