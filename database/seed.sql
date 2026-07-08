-- ============================================================
-- SANS PMS — Seed Data
-- Run AFTER schema.sql
-- ============================================================

-- Default Company
INSERT INTO companies (id, name, name_ar, cr_number, vat_number, address, address_ar, city, phone, email)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'SANS International Company',
    'شركة سانس الدولية',
    '4030000000',
    '300000000000003',
    'Jeddah, Saudi Arabia',
    'جدة، المملكة العربية السعودية',
    'Jeddah',
    '+966500000000',
    'info@sans-intl.com'
);

-- System Roles
INSERT INTO roles (id, company_id, name, name_ar, permissions, is_system_role) VALUES
(
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    'super_admin', 'مدير النظام',
    '{"all": true}', TRUE
),
(
    '00000000-0000-0000-0000-000000000011',
    '00000000-0000-0000-0000-000000000001',
    'managing_director', 'المدير العام',
    '{"projects": ["read"], "reports": ["read","export"], "hr": ["read"], "dashboard": ["read"], "ai": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000012',
    '00000000-0000-0000-0000-000000000001',
    'project_director', 'مدير المشاريع',
    '{"projects": ["read","write"], "schedule": ["read","write"], "reports": ["read","write","approve"], "hr": ["read"], "dashboard": ["read"], "ai": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000013',
    '00000000-0000-0000-0000-000000000001',
    'planning_manager', 'مدير التخطيط',
    '{"projects": ["read"], "schedule": ["read","write","import"], "boq": ["read"], "reports": ["read"], "dashboard": ["read"], "ai": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000014',
    '00000000-0000-0000-0000-000000000001',
    'commercial_manager', 'المدير التجاري',
    '{"projects": ["read"], "boq": ["read","write"], "cost": ["read","write"], "variations": ["read","write","approve"], "payments": ["read","write"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000015',
    '00000000-0000-0000-0000-000000000001',
    'project_manager', 'مدير المشروع',
    '{"projects": ["read","write"], "schedule": ["read","write"], "boq": ["read"], "cost": ["read"], "reports": ["read","write","approve"], "hr": ["read"], "equipment": ["read","write"], "materials": ["read","write"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000016',
    '00000000-0000-0000-0000-000000000001',
    'site_engineer', 'مهندس الموقع',
    '{"reports": ["read","write"], "attendance": ["read","write"], "materials": ["read","write"], "equipment": ["read"], "schedule": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000017',
    '00000000-0000-0000-0000-000000000001',
    'quantity_surveyor', 'مهندس الكميات',
    '{"boq": ["read","write"], "cost": ["read","write"], "variations": ["read","write"], "materials": ["read"], "reports": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000018',
    '00000000-0000-0000-0000-000000000001',
    'store_keeper', 'أمين المستودع',
    '{"materials": ["read","write"], "equipment": ["read"], "reports": ["read"]}',
    TRUE
),
(
    '00000000-0000-0000-0000-000000000019',
    '00000000-0000-0000-0000-000000000001',
    'employee', 'موظف',
    '{"attendance": ["read","write_own"], "leave": ["read_own","write_own"]}',
    TRUE
);

-- Default Admin User
-- Password: Admin@123 (bcrypt hash)
INSERT INTO users (id, company_id, role_id, email, password_hash, full_name, full_name_ar, status)
VALUES (
    '00000000-0000-0000-0000-000000000100',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000010',
    'admin@sans-intl.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK4aCEVqa',
    'System Administrator',
    'مدير النظام',
    'active'
);

-- Document Categories
INSERT INTO document_categories (company_id, name, name_ar, code) VALUES
('00000000-0000-0000-0000-000000000001', 'Contracts', 'العقود', 'CON'),
('00000000-0000-0000-0000-000000000001', 'Drawings', 'المخططات', 'DWG'),
('00000000-0000-0000-0000-000000000001', 'BOQ', 'جداول الكميات', 'BOQ'),
('00000000-0000-0000-0000-000000000001', 'Schedules', 'الجداول الزمنية', 'SCH'),
('00000000-0000-0000-0000-000000000001', 'RFIs', 'طلبات الاستفسار', 'RFI'),
('00000000-0000-0000-0000-000000000001', 'Submittals', 'المقدمات', 'SUB'),
('00000000-0000-0000-0000-000000000001', 'Site Instructions', 'تعليمات الموقع', 'SI'),
('00000000-0000-0000-0000-000000000001', 'Change Orders', 'أوامر التغيير', 'CO'),
('00000000-0000-0000-0000-000000000001', 'Correspondence', 'المراسلات', 'COR'),
('00000000-0000-0000-0000-000000000001', 'HSE Documents', 'وثائق السلامة', 'HSE'),
('00000000-0000-0000-0000-000000000001', 'Quality Documents', 'وثائق الجودة', 'QA'),
('00000000-0000-0000-0000-000000000001', 'Technical Reports', 'التقارير الفنية', 'TEC');

-- Departments
INSERT INTO departments (id, company_id, name, name_ar, code) VALUES
('00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0000-000000000001', 'Projects', 'المشاريع', 'PRJ'),
('00000000-0000-0000-0001-000000000002', '00000000-0000-0000-0000-000000000001', 'Engineering', 'الهندسة', 'ENG'),
('00000000-0000-0000-0001-000000000003', '00000000-0000-0000-0000-000000000001', 'Commercial', 'التجاري', 'COM'),
('00000000-0000-0000-0001-000000000004', '00000000-0000-0000-0000-000000000001', 'Operations', 'العمليات', 'OPS'),
('00000000-0000-0000-0001-000000000005', '00000000-0000-0000-0000-000000000001', 'Administration', 'الإدارة', 'ADM');

-- Positions
INSERT INTO positions (company_id, department_id, name, name_ar, code, grade) VALUES
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000001', 'Project Director', 'مدير مشاريع', 'PD', 'G1'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000001', 'Project Manager', 'مدير المشروع', 'PM', 'G2'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000001', 'Site Engineer', 'مهندس الموقع', 'SE', 'G3'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000002', 'Planning Engineer', 'مهندس التخطيط', 'PE', 'G3'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000002', 'Quantity Surveyor', 'مهندس الكميات', 'QS', 'G3'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000003', 'Commercial Manager', 'المدير التجاري', 'CM', 'G2'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000004', 'Foreman', 'مراقب', 'FM', 'G4'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000004', 'Technician', 'فني', 'TEC', 'G5'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000004', 'Store Keeper', 'أمين المستودع', 'SK', 'G5'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000005', 'HR Officer', 'موظف الموارد البشرية', 'HR', 'G4'),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0001-000000000005', 'Administrator', 'إداري', 'ADM', 'G4');

-- Sample project (KAIA Substation — matches Eslam's active project)
INSERT INTO projects (
    id, company_id, code, name, name_ar, client, client_ar,
    contract_number, project_type, status, start_date, planned_end_date,
    contract_value, currency, vat_rate, location, location_ar, city, region
) VALUES (
    '00000000-0000-0000-0002-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'SEC-6500001083',
    'Warehouse and Yard Improvement Works — Western Region',
    'أعمال تحسين المستودعات والساحات — المنطقة الغربية',
    'Saudi Electricity Company',
    'شركة الكهرباء السعودية',
    '6500001083',
    'substation',
    'active',
    '2026-06-01',
    '2027-06-30',
    0,  -- To be updated
    'SAR',
    15.00,
    'Western Region, Saudi Arabia',
    'المنطقة الغربية، المملكة العربية السعودية',
    'Jeddah',
    'Western'
);
