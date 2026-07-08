import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey,
    Integer, Numeric, Text, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    name_ar = Column(String(500))
    description = Column(Text)
    description_ar = Column(Text)
    client = Column(String(255))
    client_ar = Column(String(255))
    client_contact = Column(String(255))
    client_phone = Column(String(30))
    contract_number = Column(String(100))
    tender_number = Column(String(100))
    project_type = Column(String(50), default="civil")
    status = Column(String(50), default="planning")
    start_date = Column(Date)
    planned_end_date = Column(Date)
    actual_end_date = Column(Date)
    contract_value = Column(Numeric(18, 2))
    currency = Column(String(3), default="SAR")
    vat_rate = Column(Numeric(5, 2), default=15.00)
    retention_rate = Column(Numeric(5, 2), default=10.00)
    location = Column(String(500))
    location_ar = Column(String(500))
    city = Column(String(100))
    region = Column(String(100))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    project_manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    data_date = Column(Date)
    settings = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="projects")
    project_manager = relationship("User", foreign_keys=[project_manager_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    wbs_items = relationship("WBSItem", back_populates="project", cascade="all, delete-orphan")
    boq_items = relationship("BOQItem", back_populates="project", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    ev_snapshots = relationship("EarnedValueSnapshot", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_project = Column(String(100))
    can_submit_reports = Column(Boolean, default=False)
    can_approve_reports = Column(Boolean, default=False)
    can_edit_schedule = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="members")
    user = relationship("User")


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False)
    working_days = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5])
    hours_per_day = Column(Numeric(4, 2), default=8)
    holidays = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WBSItem(Base):
    __tablename__ = "wbs_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="CASCADE"))
    external_id = Column(String(100))
    code = Column(String(100))
    name = Column(String(1000), nullable=False)
    name_ar = Column(String(1000))
    wbs_path = Column(String(500))
    level = Column(Integer, default=1, nullable=False)
    sort_order = Column(Integer, default=0)
    is_activity = Column(Boolean, default=True)
    activity_type = Column(String(50), default="task")
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="SET NULL"))
    planned_start = Column(Date)
    planned_finish = Column(Date)
    actual_start = Column(Date)
    actual_finish = Column(Date)
    planned_duration = Column(Integer, default=0)
    actual_duration = Column(Integer)
    remaining_duration = Column(Integer)
    total_float = Column(Integer, default=0)
    free_float = Column(Integer, default=0)
    percent_complete = Column(Numeric(5, 2), default=0)
    physical_percent = Column(Numeric(5, 2), default=0)
    weight = Column(Numeric(8, 4), default=0)
    budgeted_cost = Column(Numeric(18, 2), default=0)
    actual_cost = Column(Numeric(18, 2), default=0)
    earned_value = Column(Numeric(18, 2), default=0)
    is_critical = Column(Boolean, default=False)
    constraint_type = Column(String(10), default="ASAP")
    constraint_date = Column(Date)
    notes = Column(Text)
    notes_ar = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="wbs_items")
    children = relationship("WBSItem", back_populates="parent")
    parent = relationship("WBSItem", back_populates="children", remote_side="WBSItem.id")
    boq_items = relationship("BOQItem", back_populates="activity")
    progress_updates = relationship("ProgressUpdate", back_populates="activity", cascade="all, delete-orphan")


class ActivityRelationship(Base):
    __tablename__ = "activity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    predecessor_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="CASCADE"), nullable=False)
    successor_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="CASCADE"), nullable=False)
    rel_type = Column(String(2), default="FS")
    lag = Column(Integer, default=0)

    predecessor = relationship("WBSItem", foreign_keys=[predecessor_id])
    successor = relationship("WBSItem", foreign_keys=[successor_id])


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="SET NULL"))
    name = Column(String(500), nullable=False)
    name_ar = Column(String(500))
    planned_date = Column(Date)
    actual_date = Column(Date)
    status = Column(String(50), default="pending")
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="milestones")


class ProgressUpdate(Base):
    __tablename__ = "progress_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("wbs_items.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    report_date = Column(Date, nullable=False)
    percent_complete = Column(Numeric(5, 2), nullable=False)
    actual_start = Column(Date)
    actual_finish = Column(Date)
    remaining_duration = Column(Integer)
    notes = Column(Text)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activity = relationship("WBSItem", back_populates="progress_updates")


class EarnedValueSnapshot(Base):
    __tablename__ = "earned_value_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    bcws = Column(Numeric(18, 2), default=0)
    bcwp = Column(Numeric(18, 2), default=0)
    acwp = Column(Numeric(18, 2), default=0)
    bac = Column(Numeric(18, 2), default=0)
    eac = Column(Numeric(18, 2), default=0)
    etc = Column(Numeric(18, 2), default=0)
    spi = Column(Numeric(8, 4), default=1)
    cpi = Column(Numeric(8, 4), default=1)
    cv = Column(Numeric(18, 2), default=0)
    sv = Column(Numeric(18, 2), default=0)
    percent_complete = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="ev_snapshots")
