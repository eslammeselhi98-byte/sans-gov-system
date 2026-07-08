-- ============================================================
-- SANS International Company — Construction Project Management System
-- Database Schema v1.0 | PostgreSQL 15+
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');
CREATE TYPE project_status AS ENUM ('planning', 'active', 'on_hold', 'completed', 'cancelled');
CREATE TYPE project_type AS ENUM ('substation', 'transmission_line', 'utility_network', 'civil', 'maintenance', 'other');
CREATE TYPE activity_type AS ENUM ('task', 'milestone', 'wbs', 'hammock');
CREATE TYPE relationship_type AS ENUM ('FS', 'FF', 'SS', 'SF');
CREATE TYPE constraint_type AS ENUM ('ASAP', 'ALAP', 'MSO', 'MFO', 'SNET', 'SNLT', 'FNET', 'FNLT');
CREATE TYPE report_status AS ENUM ('draft', 'submitted', 'approved', 'rejected');
CREATE TYPE document_status AS ENUM ('draft', 'under_review', 'approved', 'superseded', 'cancelled');
CREATE TYPE leave_type AS ENUM ('annual', 'sick', 'emergency', 'unpaid', 'maternity', 'hajj');
CREATE TYPE request_status AS ENUM ('pending', 'approved', 'rejected', 'cancelled');
CREATE TYPE risk_probability AS ENUM ('very_low', 'low', 'medium', 'high', 'very_high');
CREATE TYPE risk_impact AS ENUM ('negligible', 'minor', 'moderate', 'major', 'severe');
CREATE TYPE risk_status AS ENUM ('open', 'mitigated', 'closed', 'accepted');
CREATE TYPE cost_category AS ENUM ('labor', 'equipment', 'material', 'subcontract', 'overhead', 'other');
CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late', 'half_day', 'on_leave');
CREATE TYPE variation_status AS ENUM ('pending', 'under_review', 'approved', 'rejected', 'implemented');
CREATE TYPE equipment_status AS ENUM ('available', 'on_site', 'maintenance', 'out_of_service');
CREATE TYPE ai_recommendation_priority AS ENUM ('critical', 'high', 'medium', 'low');
CREATE TYPE weather_condition AS ENUM ('sunny', 'cloudy', 'partly_cloudy', 'rainy', 'stormy', 'foggy', 'dusty', 'hot');
CREATE TYPE contract_type AS ENUM ('permanent', 'temporary', 'contract', 'part_time');
CREATE TYPE file_type AS ENUM ('xer', 'xml', 'excel', 'csv', 'pdf', 'image', 'word', 'other');

-- ============================================================
-- CORE SYSTEM TABLES
-- ============================================================

CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    cr_number       VARCHAR(50),
    vat_number      VARCHAR(20),
    address         TEXT,
    address_ar      TEXT,
    city            VARCHAR(100),
    country         VARCHAR(100) DEFAULT 'Saudi Arabia',
    phone           VARCHAR(30),
    email           VARCHAR(255),
    website         VARCHAR(255),
    logo_url        VARCHAR(500),
    settings        JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    name_ar         VARCHAR(100),
    permissions     JSONB DEFAULT '{}',
    is_system_role  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, name)
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role_id         UUID REFERENCES roles(id),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    full_name_ar    VARCHAR(255),
    phone           VARCHAR(30),
    telegram_id     BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    avatar_url      VARCHAR(500),
    totp_secret     VARCHAR(100),
    totp_enabled    BOOLEAN DEFAULT FALSE,
    status          user_status DEFAULT 'active',
    last_login      TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT NOW(),
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100) NOT NULL,
    table_name      VARCHAR(100),
    record_id       UUID,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PROJECTS
-- ============================================================

CREATE TABLE projects (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    code                VARCHAR(50) NOT NULL,
    name                VARCHAR(500) NOT NULL,
    name_ar             VARCHAR(500),
    description         TEXT,
    description_ar      TEXT,
    client              VARCHAR(255),
    client_ar           VARCHAR(255),
    client_contact      VARCHAR(255),
    client_phone        VARCHAR(30),
    contract_number     VARCHAR(100),
    tender_number       VARCHAR(100),
    project_type        project_type DEFAULT 'civil',
    status              project_status DEFAULT 'planning',
    start_date          DATE,
    planned_end_date    DATE,
    actual_end_date     DATE,
    contract_value      NUMERIC(18,2),
    currency            CHAR(3) DEFAULT 'SAR',
    vat_rate            NUMERIC(5,2) DEFAULT 15.00,
    retention_rate      NUMERIC(5,2) DEFAULT 10.00,
    location            VARCHAR(500),
    location_ar         VARCHAR(500),
    city                VARCHAR(100),
    region              VARCHAR(100),
    latitude            DECIMAL(10,7),
    longitude           DECIMAL(10,7),
    project_manager_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    data_date           DATE DEFAULT CURRENT_DATE,
    settings            JSONB DEFAULT '{}',
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, code)
);

CREATE TABLE project_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_project VARCHAR(100),
    can_submit_reports BOOLEAN DEFAULT FALSE,
    can_approve_reports BOOLEAN DEFAULT FALSE,
    can_edit_schedule  BOOLEAN DEFAULT FALSE,
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- ============================================================
-- SCHEDULE / WBS
-- ============================================================

CREATE TABLE calendars (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    is_default      BOOLEAN DEFAULT FALSE,
    working_days    INTEGER[] DEFAULT '{1,2,3,4,5}',  -- 0=Sun, 6=Sat
    hours_per_day   NUMERIC(4,2) DEFAULT 8,
    holidays        JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE wbs_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id           UUID REFERENCES wbs_items(id) ON DELETE CASCADE,
    external_id         VARCHAR(100),  -- Primavera task_id
    code                VARCHAR(100),
    name                VARCHAR(1000) NOT NULL,
    name_ar             VARCHAR(1000),
    wbs_path            VARCHAR(500),
    level               INTEGER NOT NULL DEFAULT 1,
    sort_order          INTEGER DEFAULT 0,
    is_activity         BOOLEAN DEFAULT TRUE,
    activity_type       activity_type DEFAULT 'task',
    calendar_id         UUID REFERENCES calendars(id) ON DELETE SET NULL,
    planned_start       DATE,
    planned_finish      DATE,
    actual_start        DATE,
    actual_finish       DATE,
    planned_duration    INTEGER DEFAULT 0,
    actual_duration     INTEGER,
    remaining_duration  INTEGER,
    total_float         INTEGER DEFAULT 0,
    free_float          INTEGER DEFAULT 0,
    percent_complete    NUMERIC(5,2) DEFAULT 0,
    physical_percent    NUMERIC(5,2) DEFAULT 0,
    weight              NUMERIC(8,4) DEFAULT 0,
    budgeted_cost       NUMERIC(18,2) DEFAULT 0,
    actual_cost         NUMERIC(18,2) DEFAULT 0,
    earned_value        NUMERIC(18,2) DEFAULT 0,
    is_critical         BOOLEAN DEFAULT FALSE,
    constraint_type     constraint_type DEFAULT 'ASAP',
    constraint_date     DATE,
    notes               TEXT,
    notes_ar            TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE activity_relationships (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    predecessor_id  UUID NOT NULL REFERENCES wbs_items(id) ON DELETE CASCADE,
    successor_id    UUID NOT NULL REFERENCES wbs_items(id) ON DELETE CASCADE,
    rel_type        relationship_type DEFAULT 'FS',
    lag             INTEGER DEFAULT 0,
    UNIQUE(predecessor_id, successor_id, rel_type)
);

CREATE TABLE milestones (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    name            VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500),
    planned_date    DATE,
    actual_date     DATE,
    status          VARCHAR(50) DEFAULT 'pending',
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE progress_updates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id         UUID NOT NULL REFERENCES wbs_items(id) ON DELETE CASCADE,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_date         DATE NOT NULL,
    percent_complete    NUMERIC(5,2) NOT NULL,
    actual_start        DATE,
    actual_finish       DATE,
    remaining_duration  INTEGER,
    notes               TEXT,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE schedule_imports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name       VARCHAR(500) NOT NULL,
    file_type       file_type,
    file_url        VARCHAR(1000),
    activities_count INTEGER DEFAULT 0,
    relationships_count INTEGER DEFAULT 0,
    import_status   VARCHAR(50) DEFAULT 'pending',
    error_log       TEXT,
    imported_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    imported_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- BOQ
-- ============================================================

CREATE TABLE boq_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES boq_items(id) ON DELETE CASCADE,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    item_number     VARCHAR(50),
    description     TEXT NOT NULL,
    description_ar  TEXT,
    unit            VARCHAR(50),
    quantity        NUMERIC(18,4) DEFAULT 0,
    unit_rate       NUMERIC(18,4) DEFAULT 0,
    total_amount    NUMERIC(18,2) GENERATED ALWAYS AS (quantity * unit_rate) STORED,
    actual_quantity NUMERIC(18,4) DEFAULT 0,
    level           INTEGER DEFAULT 1,
    is_parent       BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COST CONTROL
-- ============================================================

CREATE TABLE budgets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    boq_item_id     UUID REFERENCES boq_items(id) ON DELETE CASCADE,
    cost_category   cost_category,
    description     TEXT,
    original_budget NUMERIC(18,2) DEFAULT 0,
    approved_budget NUMERIC(18,2) DEFAULT 0,
    currency        CHAR(3) DEFAULT 'SAR',
    valid_from      DATE,
    valid_to        DATE,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE commitments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    boq_item_id     UUID REFERENCES boq_items(id) ON DELETE SET NULL,
    po_number       VARCHAR(100),
    description     TEXT NOT NULL,
    vendor          VARCHAR(255),
    amount          NUMERIC(18,2) DEFAULT 0,
    currency        CHAR(3) DEFAULT 'SAR',
    commitment_date DATE,
    expected_delivery DATE,
    status          request_status DEFAULT 'pending',
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE actual_costs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    boq_item_id     UUID REFERENCES boq_items(id) ON DELETE SET NULL,
    commitment_id   UUID REFERENCES commitments(id) ON DELETE SET NULL,
    description     TEXT NOT NULL,
    cost_category   cost_category DEFAULT 'other',
    amount          NUMERIC(18,2) DEFAULT 0,
    currency        CHAR(3) DEFAULT 'SAR',
    cost_date       DATE NOT NULL,
    invoice_number  VARCHAR(100),
    vendor          VARCHAR(255),
    notes           TEXT,
    entered_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE variations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    variation_number VARCHAR(50),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    amount          NUMERIC(18,2) DEFAULT 0,
    currency        CHAR(3) DEFAULT 'SAR',
    time_impact_days INTEGER DEFAULT 0,
    status          variation_status DEFAULT 'pending',
    submitted_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    submitted_date  DATE,
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_date   DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payment_certificates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cert_number     INTEGER NOT NULL,
    period_from     DATE,
    period_to       DATE,
    gross_amount    NUMERIC(18,2) DEFAULT 0,
    vat_amount      NUMERIC(18,2) DEFAULT 0,
    retention_amount NUMERIC(18,2) DEFAULT 0,
    net_amount      NUMERIC(18,2) DEFAULT 0,
    cumulative_amount NUMERIC(18,2) DEFAULT 0,
    status          request_status DEFAULT 'pending',
    submitted_date  DATE,
    approved_date   DATE,
    paid_date       DATE,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, cert_number)
);

CREATE TABLE earned_value_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    bcws            NUMERIC(18,2) DEFAULT 0,  -- Planned Value
    bcwp            NUMERIC(18,2) DEFAULT 0,  -- Earned Value
    acwp            NUMERIC(18,2) DEFAULT 0,  -- Actual Cost
    bac             NUMERIC(18,2) DEFAULT 0,  -- Budget at Completion
    eac             NUMERIC(18,2) DEFAULT 0,  -- Estimate at Completion
    etc             NUMERIC(18,2) DEFAULT 0,  -- Estimate to Complete
    spi             NUMERIC(8,4) DEFAULT 1,   -- Schedule Performance Index
    cpi             NUMERIC(8,4) DEFAULT 1,   -- Cost Performance Index
    cv              NUMERIC(18,2) DEFAULT 0,  -- Cost Variance
    sv              NUMERIC(18,2) DEFAULT 0,  -- Schedule Variance
    percent_complete NUMERIC(5,2) DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, snapshot_date)
);

-- ============================================================
-- HR & EMPLOYEES
-- ============================================================

CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    code            VARCHAR(20),
    manager_id      UUID,  -- FK to employees added after
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    department_id   UUID REFERENCES departments(id) ON DELETE SET NULL,
    name            VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    code            VARCHAR(50),
    grade           VARCHAR(20),
    basic_salary    NUMERIC(12,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE employees (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    employee_number     VARCHAR(50) NOT NULL,
    full_name           VARCHAR(255) NOT NULL,
    full_name_ar        VARCHAR(255),
    nationality         VARCHAR(100),
    id_number           VARCHAR(50),  -- National ID / Iqama
    passport_number     VARCHAR(50),
    position_id         UUID REFERENCES positions(id) ON DELETE SET NULL,
    department_id       UUID REFERENCES departments(id) ON DELETE SET NULL,
    manager_id          UUID REFERENCES employees(id) ON DELETE SET NULL,
    current_project_id  UUID REFERENCES projects(id) ON DELETE SET NULL,
    hire_date           DATE,
    contract_type       contract_type DEFAULT 'permanent',
    contract_end_date   DATE,
    basic_salary        NUMERIC(12,2),
    housing_allowance   NUMERIC(12,2),
    transport_allowance NUMERIC(12,2),
    other_allowances    NUMERIC(12,2),
    currency            CHAR(3) DEFAULT 'SAR',
    iqama_expiry        DATE,
    passport_expiry     DATE,
    medical_expiry      DATE,
    safety_cert_expiry  DATE,
    phone               VARCHAR(30),
    emergency_contact   VARCHAR(255),
    emergency_phone     VARCHAR(30),
    photo_url           VARCHAR(500),
    blood_type          VARCHAR(5),
    is_active           BOOLEAN DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, employee_number)
);

-- Add FK for department manager
ALTER TABLE departments ADD CONSTRAINT fk_dept_manager
    FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL;

CREATE TABLE attendance (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
    report_date     DATE NOT NULL,
    check_in        TIME,
    check_out       TIME,
    hours_worked    NUMERIC(5,2) DEFAULT 0,
    overtime_hours  NUMERIC(5,2) DEFAULT 0,
    status          attendance_status DEFAULT 'present',
    check_in_lat    DECIMAL(10,7),
    check_in_lng    DECIMAL(10,7),
    check_out_lat   DECIMAL(10,7),
    check_out_lng   DECIMAL(10,7),
    notes           TEXT,
    verified_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, report_date)
);

CREATE TABLE leave_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type      leave_type NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    days_count      INTEGER,
    reason          TEXT,
    status          request_status DEFAULT 'pending',
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE overtime_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
    request_date    DATE NOT NULL,
    hours           NUMERIC(4,2) NOT NULL,
    reason          TEXT,
    status          request_status DEFAULT 'pending',
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE performance_reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    reviewer_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    period_from     DATE,
    period_to       DATE,
    attendance_score NUMERIC(4,2),
    quality_score   NUMERIC(4,2),
    productivity_score NUMERIC(4,2),
    teamwork_score  NUMERIC(4,2),
    overall_score   NUMERIC(4,2),
    comments        TEXT,
    recommendations TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- EQUIPMENT
-- ============================================================

CREATE TABLE equipment (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    code            VARCHAR(50) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    category        VARCHAR(100),  -- crane, excavator, generator, vehicle...
    make            VARCHAR(100),
    model           VARCHAR(100),
    year            INTEGER,
    plate_number    VARCHAR(50),
    serial_number   VARCHAR(100),
    status          equipment_status DEFAULT 'available',
    current_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    daily_rate      NUMERIC(12,2),
    last_maintenance DATE,
    next_maintenance DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, code)
);

CREATE TABLE equipment_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    equipment_id    UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    log_date        DATE NOT NULL,
    hours_worked    NUMERIC(5,2) DEFAULT 0,
    fuel_consumed   NUMERIC(8,2) DEFAULT 0,
    operator_id     UUID REFERENCES employees(id) ON DELETE SET NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MATERIALS
-- ============================================================

CREATE TABLE materials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    code            VARCHAR(100) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500),
    category        VARCHAR(100),
    unit            VARCHAR(50),
    min_stock       NUMERIC(12,4) DEFAULT 0,
    current_stock   NUMERIC(12,4) DEFAULT 0,
    unit_cost       NUMERIC(12,4) DEFAULT 0,
    supplier        VARCHAR(255),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, code)
);

CREATE TABLE material_receipts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    received_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    receipt_date    DATE NOT NULL,
    delivery_note   VARCHAR(100),
    supplier        VARCHAR(255),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE material_receipt_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_id      UUID NOT NULL REFERENCES material_receipts(id) ON DELETE CASCADE,
    material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    quantity        NUMERIC(12,4) NOT NULL,
    unit_cost       NUMERIC(12,4) DEFAULT 0,
    total_cost      NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_cost) STORED
);

CREATE TABLE material_issues (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    issued_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    issue_date      DATE NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE material_issue_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_id        UUID NOT NULL REFERENCES material_issues(id) ON DELETE CASCADE,
    material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    quantity        NUMERIC(12,4) NOT NULL,
    unit_cost       NUMERIC(12,4) DEFAULT 0
);

-- ============================================================
-- DAILY REPORTS
-- ============================================================

CREATE TABLE daily_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_date         DATE NOT NULL,
    submitted_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    weather_condition   weather_condition DEFAULT 'sunny',
    weather_temp        INTEGER,
    weather_humidity    INTEGER,
    site_conditions     TEXT,
    work_performed      TEXT,
    work_performed_ar   TEXT,
    delays_description  TEXT,
    constraints_description TEXT,
    safety_incidents    TEXT,
    visitor_log         TEXT,
    overall_progress    NUMERIC(5,2),
    status              report_status DEFAULT 'draft',
    submitted_at        TIMESTAMPTZ,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, report_date)
);

CREATE TABLE daily_report_activities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    activity_name   VARCHAR(500),
    work_done       TEXT,
    progress_today  NUMERIC(5,2) DEFAULT 0,
    cumulative_progress NUMERIC(5,2) DEFAULT 0,
    crew_count      INTEGER DEFAULT 0,
    remarks         TEXT
);

CREATE TABLE daily_report_manpower (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    employee_id     UUID REFERENCES employees(id) ON DELETE SET NULL,
    position_id     UUID REFERENCES positions(id) ON DELETE SET NULL,
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    hours_worked    NUMERIC(5,2) DEFAULT 8,
    overtime_hours  NUMERIC(5,2) DEFAULT 0
);

CREATE TABLE daily_report_equipment (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    equipment_id    UUID REFERENCES equipment(id) ON DELETE SET NULL,
    equipment_name  VARCHAR(255),
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    hours_worked    NUMERIC(5,2) DEFAULT 0,
    fuel_consumed   NUMERIC(8,2) DEFAULT 0,
    remarks         TEXT
);

CREATE TABLE daily_report_materials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    material_id     UUID REFERENCES materials(id) ON DELETE SET NULL,
    material_name   VARCHAR(500),
    activity_id     UUID REFERENCES wbs_items(id) ON DELETE SET NULL,
    quantity        NUMERIC(12,4),
    unit            VARCHAR(50),
    remarks         TEXT
);

CREATE TABLE daily_report_photos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    file_url        VARCHAR(1000) NOT NULL,
    caption         VARCHAR(500),
    latitude        DECIMAL(10,7),
    longitude       DECIMAL(10,7),
    taken_at        TIMESTAMPTZ,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DOCUMENT CONTROL
-- ============================================================

CREATE TABLE document_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    code            VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    category_id     UUID REFERENCES document_categories(id) ON DELETE SET NULL,
    doc_number      VARCHAR(100),
    title           VARCHAR(500) NOT NULL,
    title_ar        VARCHAR(500),
    description     TEXT,
    file_url        VARCHAR(1000),
    file_size       BIGINT,
    file_mime       VARCHAR(100),
    version         VARCHAR(20) DEFAULT '1.0',
    revision        VARCHAR(10) DEFAULT 'A',
    status          document_status DEFAULT 'draft',
    tags            TEXT[],
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at     TIMESTAMPTZ DEFAULT NOW(),
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE document_revisions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version         VARCHAR(20),
    revision        VARCHAR(10),
    file_url        VARCHAR(1000),
    file_size       BIGINT,
    change_summary  TEXT,
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RISKS
-- ============================================================

CREATE TABLE risks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    risk_number     VARCHAR(20),
    title           VARCHAR(500) NOT NULL,
    title_ar        VARCHAR(500),
    description     TEXT,
    category        VARCHAR(100),
    probability     risk_probability DEFAULT 'medium',
    impact          risk_impact DEFAULT 'moderate',
    risk_score      INTEGER GENERATED ALWAYS AS (
        CASE probability
            WHEN 'very_low' THEN 1 WHEN 'low' THEN 2
            WHEN 'medium' THEN 3 WHEN 'high' THEN 4 WHEN 'very_high' THEN 5
        END *
        CASE impact
            WHEN 'negligible' THEN 1 WHEN 'minor' THEN 2
            WHEN 'moderate' THEN 3 WHEN 'major' THEN 4 WHEN 'severe' THEN 5
        END
    ) STORED,
    mitigation_plan TEXT,
    contingency_plan TEXT,
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    status          risk_status DEFAULT 'open',
    review_date     DATE,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TELEGRAM BOT
-- ============================================================

CREATE TABLE telegram_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    telegram_id     BIGINT NOT NULL UNIQUE,
    chat_id         BIGINT,
    username        VARCHAR(100),
    language        CHAR(2) DEFAULT 'ar',
    state           VARCHAR(100) DEFAULT 'idle',
    state_data      JSONB DEFAULT '{}',
    last_active     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AI & RECOMMENDATIONS
-- ============================================================

CREATE TABLE ai_analyses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    analysis_type   VARCHAR(100) NOT NULL,
    input_data      JSONB DEFAULT '{}',
    result          JSONB DEFAULT '{}',
    model_used      VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    analysis_id     UUID REFERENCES ai_analyses(id) ON DELETE SET NULL,
    category        VARCHAR(100),
    title           VARCHAR(500),
    title_ar        VARCHAR(500),
    recommendation  TEXT NOT NULL,
    recommendation_ar TEXT,
    priority        ai_recommendation_priority DEFAULT 'medium',
    action_required BOOLEAN DEFAULT FALSE,
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE kpi_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    spi             NUMERIC(8,4),
    cpi             NUMERIC(8,4),
    percent_complete NUMERIC(5,2),
    manpower_count  INTEGER,
    equipment_count INTEGER,
    safety_incidents INTEGER DEFAULT 0,
    reports_submitted INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_company_id ON users(company_id);
CREATE INDEX idx_projects_company_id ON projects(company_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_wbs_project_id ON wbs_items(project_id);
CREATE INDEX idx_wbs_parent_id ON wbs_items(parent_id);
CREATE INDEX idx_wbs_activity_type ON wbs_items(activity_type);
CREATE INDEX idx_wbs_critical ON wbs_items(is_critical);
CREATE INDEX idx_relationships_predecessor ON activity_relationships(predecessor_id);
CREATE INDEX idx_relationships_successor ON activity_relationships(successor_id);
CREATE INDEX idx_boq_project_id ON boq_items(project_id);
CREATE INDEX idx_boq_parent_id ON boq_items(parent_id);
CREATE INDEX idx_boq_activity_id ON boq_items(activity_id);
CREATE INDEX idx_employees_company ON employees(company_id);
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_user_id ON employees(user_id);
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, report_date);
CREATE INDEX idx_attendance_project ON attendance(project_id);
CREATE INDEX idx_daily_reports_project_date ON daily_reports(project_id, report_date);
CREATE INDEX idx_daily_reports_status ON daily_reports(status);
CREATE INDEX idx_actual_costs_project ON actual_costs(project_id);
CREATE INDEX idx_actual_costs_date ON actual_costs(cost_date);
CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_category ON documents(category_id);
CREATE INDEX idx_risks_project ON risks(project_id);
CREATE INDEX idx_risks_status ON risks(status);
CREATE INDEX idx_ev_snapshots_project_date ON earned_value_snapshots(project_id, snapshot_date);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_table ON audit_logs(table_name, record_id);
CREATE INDEX idx_progress_updates_activity ON progress_updates(activity_id);
CREATE INDEX idx_ai_recommendations_project ON ai_recommendations(project_id);

-- Full-text search indexes
CREATE INDEX idx_documents_title_fts ON documents USING gin(to_tsvector('arabic', COALESCE(title_ar, '') || ' ' || COALESCE(title, '')));
CREATE INDEX idx_wbs_name_fts ON wbs_items USING gin(to_tsvector('simple', COALESCE(name_ar, '') || ' ' || name));

-- ============================================================
-- VIEWS
-- ============================================================

CREATE OR REPLACE VIEW v_project_summary AS
SELECT
    p.id,
    p.code,
    p.name,
    p.name_ar,
    p.client,
    p.contract_value,
    p.currency,
    p.status,
    p.start_date,
    p.planned_end_date,
    p.data_date,
    COALESCE(u.full_name, '') AS project_manager,
    COALESCE(wbs_stats.activity_count, 0) AS activity_count,
    COALESCE(wbs_stats.avg_progress, 0) AS avg_progress,
    COALESCE(wbs_stats.critical_count, 0) AS critical_activities,
    COALESCE(cost_stats.total_actual, 0) AS total_actual_cost,
    COALESCE(cost_stats.total_committed, 0) AS total_committed,
    (p.planned_end_date - CURRENT_DATE) AS days_remaining
FROM projects p
LEFT JOIN users u ON p.project_manager_id = u.id
LEFT JOIN (
    SELECT
        project_id,
        COUNT(*) FILTER (WHERE is_activity) AS activity_count,
        AVG(percent_complete) FILTER (WHERE is_activity) AS avg_progress,
        COUNT(*) FILTER (WHERE is_critical AND is_activity) AS critical_count
    FROM wbs_items
    GROUP BY project_id
) wbs_stats ON wbs_stats.project_id = p.id
LEFT JOIN (
    SELECT project_id, SUM(amount) AS total_actual FROM actual_costs GROUP BY project_id
) cost_stats ON cost_stats.project_id = p.id
LEFT JOIN (
    SELECT project_id, SUM(amount) AS total_committed FROM commitments GROUP BY project_id
) comm_stats ON comm_stats.project_id = p.id;

CREATE OR REPLACE VIEW v_employee_summary AS
SELECT
    e.id,
    e.employee_number,
    e.full_name,
    e.full_name_ar,
    e.nationality,
    e.iqama_expiry,
    e.passport_expiry,
    e.is_active,
    p.name AS position_name,
    p.name_ar AS position_name_ar,
    d.name AS department_name,
    d.name_ar AS department_name_ar,
    proj.name AS current_project,
    COALESCE(att.days_present, 0) AS days_present_this_month,
    COALESCE(att.total_hours, 0) AS hours_this_month,
    COALESCE(att.total_overtime, 0) AS overtime_this_month,
    CASE
        WHEN e.iqama_expiry < CURRENT_DATE + 30 THEN 'expiring_soon'
        WHEN e.iqama_expiry < CURRENT_DATE THEN 'expired'
        ELSE 'valid'
    END AS iqama_status
FROM employees e
LEFT JOIN positions p ON e.position_id = p.id
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN projects proj ON e.current_project_id = proj.id
LEFT JOIN (
    SELECT
        employee_id,
        COUNT(*) AS days_present,
        SUM(hours_worked) AS total_hours,
        SUM(overtime_hours) AS total_overtime
    FROM attendance
    WHERE EXTRACT(MONTH FROM report_date) = EXTRACT(MONTH FROM CURRENT_DATE)
    AND EXTRACT(YEAR FROM report_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY employee_id
) att ON att.employee_id = e.id;

CREATE OR REPLACE VIEW v_daily_report_summary AS
SELECT
    dr.id,
    dr.project_id,
    p.name AS project_name,
    p.name_ar AS project_name_ar,
    dr.report_date,
    dr.weather_condition,
    dr.weather_temp,
    dr.status,
    dr.overall_progress,
    u.full_name AS submitted_by_name,
    dr.submitted_at,
    COUNT(DISTINCT drm.id) AS manpower_count,
    COUNT(DISTINCT dre.id) AS equipment_count,
    COUNT(DISTINCT drp.id) AS photos_count,
    COUNT(DISTINCT dra.id) AS activities_count
FROM daily_reports dr
JOIN projects p ON dr.project_id = p.id
LEFT JOIN users u ON dr.submitted_by = u.id
LEFT JOIN daily_report_manpower drm ON drm.report_id = dr.id
LEFT JOIN daily_report_equipment dre ON dre.report_id = dr.id
LEFT JOIN daily_report_photos drp ON drp.report_id = dr.id
LEFT JOIN daily_report_activities dra ON dra.report_id = dr.id
GROUP BY dr.id, p.name, p.name_ar, u.full_name;

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_wbs_updated_at BEFORE UPDATE ON wbs_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_boq_updated_at BEFORE UPDATE ON boq_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_employees_updated_at BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_daily_reports_updated_at BEFORE UPDATE ON daily_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Auto-update material stock on receipt
CREATE OR REPLACE FUNCTION update_material_stock_on_receipt()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE materials SET current_stock = current_stock + NEW.quantity
    WHERE id = NEW.material_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_material_receipt_stock AFTER INSERT ON material_receipt_items
    FOR EACH ROW EXECUTE FUNCTION update_material_stock_on_receipt();

-- Reduce stock on issue
CREATE OR REPLACE FUNCTION update_material_stock_on_issue()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE materials SET current_stock = current_stock - NEW.quantity
    WHERE id = NEW.material_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_material_issue_stock AFTER INSERT ON material_issue_items
    FOR EACH ROW EXECUTE FUNCTION update_material_stock_on_issue();

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

-- Calculate project progress based on weighted activities
CREATE OR REPLACE FUNCTION calculate_project_progress(p_project_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    v_progress NUMERIC;
BEGIN
    SELECT
        CASE WHEN SUM(weight) = 0 THEN 0
             ELSE SUM(weight * percent_complete) / SUM(weight)
        END INTO v_progress
    FROM wbs_items
    WHERE project_id = p_project_id AND is_activity = TRUE;

    UPDATE projects SET updated_at = NOW() WHERE id = p_project_id;
    RETURN COALESCE(v_progress, 0);
END;
$$ LANGUAGE plpgsql;

-- Snapshot earned value for a project
CREATE OR REPLACE FUNCTION snapshot_earned_value(p_project_id UUID, p_date DATE DEFAULT CURRENT_DATE)
RETURNS VOID AS $$
DECLARE
    v_bcws NUMERIC;
    v_bcwp NUMERIC;
    v_acwp NUMERIC;
    v_bac  NUMERIC;
    v_eac  NUMERIC;
    v_spi  NUMERIC;
    v_cpi  NUMERIC;
BEGIN
    SELECT COALESCE(SUM(budgeted_cost), 0) INTO v_bac
    FROM wbs_items WHERE project_id = p_project_id AND is_activity;

    SELECT COALESCE(SUM(amount), 0) INTO v_acwp
    FROM actual_costs WHERE project_id = p_project_id AND cost_date <= p_date;

    SELECT COALESCE(SUM(budgeted_cost * percent_complete / 100), 0) INTO v_bcwp
    FROM wbs_items WHERE project_id = p_project_id AND is_activity;

    -- Simplified BCWS: linear interpolation
    SELECT COALESCE(
        v_bac * EXTRACT(EPOCH FROM (p_date - MIN(planned_start)))
                / NULLIF(EXTRACT(EPOCH FROM (MAX(planned_finish) - MIN(planned_start))), 0),
        0
    ) INTO v_bcws
    FROM wbs_items WHERE project_id = p_project_id AND is_activity;

    v_spi := CASE WHEN v_bcws = 0 THEN 1 ELSE v_bcwp / v_bcws END;
    v_cpi := CASE WHEN v_acwp = 0 THEN 1 ELSE v_bcwp / v_acwp END;
    v_eac := CASE WHEN v_cpi = 0 THEN v_bac ELSE v_bac / v_cpi END;

    INSERT INTO earned_value_snapshots
        (project_id, snapshot_date, bcws, bcwp, acwp, bac, eac, etc, spi, cpi, cv, sv)
    VALUES (
        p_project_id, p_date, v_bcws, v_bcwp, v_acwp, v_bac, v_eac,
        v_eac - v_acwp, v_spi, v_cpi,
        v_bcwp - v_acwp, v_bcwp - v_bcws
    )
    ON CONFLICT (project_id, snapshot_date)
    DO UPDATE SET
        bcws = EXCLUDED.bcws, bcwp = EXCLUDED.bcwp, acwp = EXCLUDED.acwp,
        bac = EXCLUDED.bac, eac = EXCLUDED.eac, etc = EXCLUDED.etc,
        spi = EXCLUDED.spi, cpi = EXCLUDED.cpi, cv = EXCLUDED.cv, sv = EXCLUDED.sv;
END;
$$ LANGUAGE plpgsql;
