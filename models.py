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
