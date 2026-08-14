from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user') # 'user', 'admin', 'superadmin'
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    phone_no = db.Column(db.String(20), unique=True, nullable=True)
    place = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)

    department = db.relationship('Department', backref='admins')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    officer_name = db.Column(db.String(100), nullable=True)
    officer_phone = db.Column(db.String(20), nullable=True)
    officer_email = db.Column(db.String(120), nullable=True)

class Consignment(db.Model):
    __tablename__ = 'consignments'
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Submitted') # Submitted, Pending, Under Review, Approved, Completed, Closed
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    attachment_url = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submitter = db.relationship('User', foreign_keys=[user_id], backref='submitted_consignments')
    admin = db.relationship('User', foreign_keys=[assigned_admin_id], backref='assigned_consignments')
    department = db.relationship('Department', backref='consignments')

class PendingWork(db.Model):
    __tablename__ = 'pending_works'
    id = db.Column(db.Integer, primary_key=True) # Automatic generation starting 1
    work_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    local_body = db.Column(db.String(255), nullable=False)
    ward_no = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    remarks = db.Column(db.Text, nullable=True)
    installment_1 = db.Column(db.Integer, nullable=True, default=0)
    installment_2 = db.Column(db.Integer, nullable=True, default=0)
    installment_3 = db.Column(db.Integer, nullable=True, default=0)
    balance_amount = db.Column(db.Integer, nullable=True, default=0)
    file_status = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    contractor_name = db.Column(db.String(255), nullable=True)
    contractor_address = db.Column(db.Text, nullable=True)
    contractor_phone = db.Column(db.String(50), nullable=True)

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True) # auto index
    vehicle_number = db.Column(db.String(50), nullable=False, unique=True)
    vehicle_model = db.Column(db.String(100), nullable=False)
    vehicle_year = db.Column(db.Integer, nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    driver_contract = db.Column(db.String(100), nullable=True)
    driver_license = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False) # 'owned', 'shared', 'other'
    status = db.Column(db.String(50), nullable=False, default='Pending') # 'Active' or 'Pending'


class SystemBalance(db.Model):
    __tablename__ = 'system_balances'
    id = db.Column(db.Integer, primary_key=True)
    total_balance = db.Column(db.Float, default=200000.0)
    current_balance = db.Column(db.Float, default=150000.0)
    used_up_balance = db.Column(db.Float, default=50000.0)


class Road(db.Model):
    __tablename__ = 'roads'
    id = db.Column(db.Integer, primary_key=True)
    constituency = db.Column(db.String(100), nullable=True)
    mla_name = db.Column(db.String(100), nullable=True)
    local_govt_name = db.Column(db.String(100), nullable=True)
    local_govt_type = db.Column(db.String(100), nullable=True)
    road_name = db.Column(db.String(200), nullable=False)
    road_width = db.Column(db.Float, nullable=True, default=0.0)
    road_length = db.Column(db.Float, nullable=True, default=0.0)
    estimate_cost = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    remarks = db.Column(db.Text, nullable=True)
    approval_date = db.Column(db.String(100), nullable=True)
    installment_1 = db.Column(db.Integer, nullable=True, default=0)
    installment_2 = db.Column(db.Integer, nullable=True, default=0)
    installment_3 = db.Column(db.Integer, nullable=True, default=0)
    contractor_name = db.Column(db.String(255), nullable=True)
    contractor_address = db.Column(db.Text, nullable=True)
    contractor_phone = db.Column(db.String(50), nullable=True)
    attachment_url = db.Column(db.String(500), nullable=True)


class FundManagement(db.Model):
    __tablename__ = 'fund_management'
    id = db.Column(db.Integer, primary_key=True)
    financial_year = db.Column(db.String(50), nullable=False)
    constituency = db.Column(db.String(100), nullable=False)
    mla_name = db.Column(db.String(100), nullable=False)
    fund_type = db.Column(db.String(50), nullable=False) # 'MLA-SDF' or 'LAC-ADF'
    annual_fund_allocation = db.Column(db.Float, default=0.0)
    previous_year_balance = db.Column(db.Float, default=0.0)
    total_available_fund = db.Column(db.Float, default=0.0)
    amount_recommended = db.Column(db.Float, default=0.0)
    amount_sanctioned = db.Column(db.Float, default=0.0)
    amount_released = db.Column(db.Float, default=0.0)
    amount_utilized = db.Column(db.Float, default=0.0)
    balance_amount = db.Column(db.Float, default=0.0)
    number_of_projects = db.Column(db.Integer, default=0)
    pending_projects = db.Column(db.Integer, default=0)
    completed_projects = db.Column(db.Integer, default=0)


class LAC_ADF_Project(db.Model):
    __tablename__ = 'lac_adf_projects'
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255), nullable=False)
    project_category = db.Column(db.String(100), nullable=True)
    project_description = db.Column(db.Text, nullable=True)
    constituency = db.Column(db.String(100), nullable=False)
    local_body = db.Column(db.String(100), nullable=False)
    ward = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    beneficiary_institution = db.Column(db.String(255), nullable=True)
    beneficiary_details = db.Column(db.Text, nullable=True)
    mla_recommendation_date = db.Column(db.String(100), nullable=True)
    estimated_project_cost = db.Column(db.Float, default=0.0)
    mla_adf_amount = db.Column(db.Float, default=0.0)
    other_fund_contribution = db.Column(db.Float, default=0.0)
    implementing_department = db.Column(db.String(255), nullable=True)
    implementing_agency = db.Column(db.String(255), nullable=True)
    project_officer = db.Column(db.String(100), nullable=True)
    priority = db.Column(db.String(50), nullable=True) # 'High', 'Medium', 'Low'
    project_status = db.Column(db.String(50), default='Proposed') # 'Proposed', 'Approved', 'Execution', 'Completed'


class ApprovalSanctionTracking(db.Model):
    __tablename__ = 'approval_sanction_tracking'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('lac_adf_projects.id'), nullable=False)
    administrative_department = db.Column(db.String(255), nullable=True)
    mla_recommendation = db.Column(db.String(255), nullable=True)
    administrative_sanction_no = db.Column(db.String(100), nullable=True)
    administrative_sanction_date = db.Column(db.String(100), nullable=True)
    technical_sanction_no = db.Column(db.String(100), nullable=True)
    technical_sanction_date = db.Column(db.String(100), nullable=True)
    financial_concurrence_no = db.Column(db.String(100), nullable=True)
    financial_concurrence_date = db.Column(db.String(100), nullable=True)
    detailed_estimate_prepared = db.Column(db.Boolean, default=False)
    tender_quotation_required = db.Column(db.Boolean, default=False)
    tender_date = db.Column(db.String(100), nullable=True)
    work_order_no = db.Column(db.String(100), nullable=True)
    work_order_date = db.Column(db.String(100), nullable=True)
    agreement_no = db.Column(db.String(100), nullable=True)
    agreement_date = db.Column(db.String(100), nullable=True)


class ProjectExecution(db.Model):
    __tablename__ = 'project_executions'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('lac_adf_projects.id'), nullable=False)
    contractor_agency = db.Column(db.String(255), nullable=True)
    work_order_amount = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.String(100), nullable=True)
    scheduled_completion_date = db.Column(db.String(100), nullable=True)
    actual_completion_date = db.Column(db.String(100), nullable=True)
    physical_progress_pct = db.Column(db.Float, default=0.0)
    financial_progress_pct = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    running_bill_no = db.Column(db.String(100), nullable=True)
    last_payment_date = db.Column(db.String(100), nullable=True)
    current_status = db.Column(db.String(100), nullable=True)
    delay_reason = db.Column(db.Text, nullable=True)
    revised_completion_date = db.Column(db.String(100), nullable=True)


class PaymentUtilization(db.Model):
    __tablename__ = 'payment_utilization'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('lac_adf_projects.id'), nullable=False)
    bill_no = db.Column(db.String(100), nullable=True)
    bill_date = db.Column(db.String(100), nullable=True)
    bill_amount = db.Column(db.Float, default=0.0)
    amount_approved = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    payment_date = db.Column(db.String(100), nullable=True)
    payment_reference = db.Column(db.String(255), nullable=True)
    cumulative_expenditure = db.Column(db.Float, default=0.0)
    remaining_project_fund = db.Column(db.Float, default=0.0)
    uc_submitted = db.Column(db.Boolean, default=False)
    uc_date = db.Column(db.String(100), nullable=True)


class MonitoringInspection(db.Model):
    __tablename__ = 'monitoring_inspection'
    id = db.Column(db.Integer, primary_key=True)
    inspection_id = db.Column(db.String(100), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('lac_adf_projects.id'), nullable=False)
    inspection_date = db.Column(db.String(100), nullable=True)
    inspection_officer = db.Column(db.String(255), nullable=True)
    physical_progress_pct = db.Column(db.Float, default=0.0)
    financial_progress_pct = db.Column(db.Float, default=0.0)
    quality_status = db.Column(db.String(100), nullable=True)
    issues_identified = db.Column(db.Text, nullable=True)
    corrective_action = db.Column(db.Text, nullable=True)
    next_inspection_date = db.Column(db.String(100), nullable=True)
    inspection_report = db.Column(db.String(500), nullable=True)
    photographs = db.Column(db.String(500), nullable=True)
    remarks = db.Column(db.Text, nullable=True)


class CompletionAssetRegister(db.Model):
    __tablename__ = 'completion_asset_register'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('lac_adf_projects.id'), nullable=False)
    completion_certificate_no = db.Column(db.String(100), nullable=True)
    completion_date = db.Column(db.String(100), nullable=True)
    final_cost = db.Column(db.Float, default=0.0)
    final_expenditure = db.Column(db.Float, default=0.0)
    asset_created = db.Column(db.String(255), nullable=True)
    asset_location = db.Column(db.String(255), nullable=True)
    asset_custodian_department = db.Column(db.String(255), nullable=True)
    handover_date = db.Column(db.String(100), nullable=True)
    handover_document = db.Column(db.String(500), nullable=True)
    maintenance_responsibility = db.Column(db.String(255), nullable=True)
    maintenance_period = db.Column(db.String(100), nullable=True)
    asset_status = db.Column(db.String(100), nullable=True)


