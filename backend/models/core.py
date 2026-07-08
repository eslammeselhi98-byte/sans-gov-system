import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey,
    Integer, Numeric, Text, BigInteger, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.database import Base


# ─── BOQ ──────────────────────────────────────────────────────

class BOQItem(Base):
    __tablename__ = "boq_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("boq_items.id", ondelete="CASCADE"))
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    item_number = Column(String(50))
    description = Column(Text, nullable=False)
    description_ar = Column(Text)
    unit = Column(String(50))
    quantity = Column(Numeric(18, 4), default=0)
    unit_rate = Column(Numeric(18, 4), default=0)
    actual_quantity = Column(Numeric(18, 4), default=0)
    level = Column(Integer, default=1)
    is_parent = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="boq_items")
    activity = relationship("WBSItem", back_populates="boq_items")
    children = relationship("BOQItem", back_populates="parent")
    parent = relationship("BOQItem", back_populates="children", remote_side="BOQItem.id")

    @property
    def total_amount(self):
        return float(self.quantity or 0) * float(self.unit_rate or 0)


# ─── COST CONTROL ────────────────────────────────────────────

class ActualCost(Base):
    __tablename__ = "actual_costs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    boq_item_id = Column(UUID(as_uuid=True), ForeignKey("boq_items.id", ondelete="SET NULL"))
    description = Column(Text, nullable=False)
    cost_category = Column(String(50), default="other")
    amount = Column(Numeric(18, 2), default=0)
    currency = Column(String(3), default="SAR")
    cost_date = Column(Date, nullable=False)
    invoice_number = Column(String(100))
    vendor = Column(String(255))
    notes = Column(Text)
    entered_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Variation(Base):
    __tablename__ = "variations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    variation_number = Column(String(50))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    amount = Column(Numeric(18, 2), default=0)
    currency = Column(String(3), default="SAR")
    time_impact_days = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    submitted_date = Column(Date)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaymentCertificate(Base):
    __tablename__ = "payment_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    cert_number = Column(Integer, nullable=False)
    period_from = Column(Date)
    period_to = Column(Date)
    gross_amount = Column(Numeric(18, 2), default=0)
    vat_amount = Column(Numeric(18, 2), default=0)
    retention_amount = Column(Numeric(18, 2), default=0)
    net_amount = Column(Numeric(18, 2), default=0)
    cumulative_amount = Column(Numeric(18, 2), default=0)
    status = Column(String(20), default="pending")
    submitted_date = Column(Date)
    approved_date = Column(Date)
    paid_date = Column(Date)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── DAILY REPORTS ───────────────────────────────────────────

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    report_date = Column(Date, nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    weather_condition = Column(String(30), default="sunny")
    weather_temp = Column(Integer)
    weather_humidity = Column(Integer)
    site_conditions = Column(Text)
    work_performed = Column(Text)
    work_performed_ar = Column(Text)
    delays_description = Column(Text)
    constraints_description = Column(Text)
    safety_incidents = Column(Text)
    visitor_log = Column(Text)
    overall_progress = Column(Numeric(5, 2))
    status = Column(String(20), default="draft")
    submitted_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="daily_reports")
    submitter = relationship("User", foreign_keys=[submitted_by])
    activities = relationship("DailyReportActivity", back_populates="report", cascade="all, delete-orphan")
    manpower = relationship("DailyReportManpower", back_populates="report", cascade="all, delete-orphan")
    equipment_log = relationship("DailyReportEquipment", back_populates="report", cascade="all, delete-orphan")
    materials_log = relationship("DailyReportMaterial", back_populates="report", cascade="all, delete-orphan")
    photos = relationship("DailyReportPhoto", back_populates="report", cascade="all, delete-orphan")


class DailyReportActivity(Base):
    __tablename__ = "daily_report_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    activity_name = Column(String(500))
    work_done = Column(Text)
    progress_today = Column(Numeric(5, 2), default=0)
    cumulative_progress = Column(Numeric(5, 2), default=0)
    crew_count = Column(Integer, default=0)
    remarks = Column(Text)

    report = relationship("DailyReport", back_populates="activities")


class DailyReportManpower(Base):
    __tablename__ = "daily_report_manpower"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="SET NULL"))
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    hours_worked = Column(Numeric(5, 2), default=8)
    overtime_hours = Column(Numeric(5, 2), default=0)

    report = relationship("DailyReport", back_populates="manpower")


class DailyReportEquipment(Base):
    __tablename__ = "daily_report_equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"))
    equipment_name = Column(String(255))
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    hours_worked = Column(Numeric(5, 2), default=0)
    fuel_consumed = Column(Numeric(8, 2), default=0)
    remarks = Column(Text)

    report = relationship("DailyReport", back_populates="equipment_log")


class DailyReportMaterial(Base):
    __tablename__ = "daily_report_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"))
    material_name = Column(String(500))
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    quantity = Column(Numeric(12, 4))
    unit = Column(String(50))
    remarks = Column(Text)

    report = relationship("DailyReport", back_populates="materials_log")


class DailyReportPhoto(Base):
    __tablename__ = "daily_report_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(1000), nullable=False)
    caption = Column(String(500))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    taken_at = Column(DateTime(timezone=True))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DailyReport", back_populates="photos")


# ─── EQUIPMENT & MATERIALS ───────────────────────────────────

class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    category = Column(String(100))
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    plate_number = Column(String(50))
    serial_number = Column(String(100))
    status = Column(String(30), default="available")
    current_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    daily_rate = Column(Numeric(12, 2))
    last_maintenance = Column(Date)
    next_maintenance = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(100), nullable=False)
    name = Column(String(500), nullable=False)
    name_ar = Column(String(500))
    category = Column(String(100))
    unit = Column(String(50))
    min_stock = Column(Numeric(12, 4), default=0)
    current_stock = Column(Numeric(12, 4), default=0)
    unit_cost = Column(Numeric(12, 4), default=0)
    supplier = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── DOCUMENTS ───────────────────────────────────────────────

class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    code = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="category")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("document_categories.id", ondelete="SET NULL"))
    doc_number = Column(String(100))
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    description = Column(Text)
    file_url = Column(String(1000))
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    version = Column(String(20), default="1.0")
    revision = Column(String(10), default="A")
    status = Column(String(30), default="draft")
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("DocumentCategory", back_populates="documents")
    revisions = relationship("DocumentRevision", back_populates="document", cascade="all, delete-orphan")


class DocumentRevision(Base):
    __tablename__ = "document_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(20))
    revision = Column(String(10))
    file_url = Column(String(1000))
    file_size = Column(BigInteger)
    change_summary = Column(Text)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="revisions")


# ─── RISKS ───────────────────────────────────────────────────

class Risk(Base):
    __tablename__ = "risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    risk_number = Column(String(20))
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    description = Column(Text)
    category = Column(String(100))
    probability = Column(String(20), default="medium")
    impact = Column(String(20), default="moderate")
    mitigation_plan = Column(Text)
    contingency_plan = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(String(20), default="open")
    review_date = Column(Date)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="risks")


# ─── AI ──────────────────────────────────────────────────────

class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    category = Column(String(100))
    title = Column(String(500))
    title_ar = Column(String(500))
    recommendation = Column(Text, nullable=False)
    recommendation_ar = Column(Text)
    priority = Column(String(20), default="medium")
    action_required = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    chat_id = Column(BigInteger)
    username = Column(String(100))
    language = Column(String(2), default="ar")
    state = Column(String(100), default="idle")
    state_data = Column(JSONB, default=dict)
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
