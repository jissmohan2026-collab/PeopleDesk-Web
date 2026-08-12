


from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_babel import Babel, _
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, bcrypt, User, Department, Consignment, PendingWork, Vehicle, SystemBalance
import uuid
from datetime import datetime
import os
import csv
import io
from flask import Response
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def get_locale():
    return session.get('lang', request.accept_languages.best_match(app.config['LANGUAGES']))

babel = Babel(app, locale_selector=get_locale)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in app.config['LANGUAGES']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Public Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/track', methods=['GET', 'POST'])
def track():
    consignment = None
    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id')
        consignment = Consignment.query.filter_by(tracking_id=tracking_id).first()
        if not consignment:
            flash(_('No consignment found with that tracking ID.), '), ')')
    return render_template('track.html', consignment=consignment)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'superadmin':
            return redirect(url_for('superadmin_dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                if user.role == 'superadmin':
                    return redirect(url_for('superadmin_dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(str(e), 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            name = request.form.get('name')
            address = request.form.get('address')
            phone_no = request.form.get('phone_no')
            place = request.form.get('place')
            district = request.form.get('district')
            
            if User.query.filter_by(username=username).first():
                flash(_('Username already exists.), '), ')')
                return redirect(url_for('register'))
            if phone_no and User.query.filter_by(phone_no=phone_no).first():
                flash(_('Phone number already registered.), '), ')')
                return redirect(url_for('register'))
                
            new_user = User(
                username=username, role='user',
                name=name, address=address, phone_no=phone_no, place=place, district=district
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('user_dashboard'))
        except Exception as e:
            flash(str(e), 'danger')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- User Routes ---
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        return redirect(url_for('index'))
    consignments = Consignment.query.filter_by(user_id=current_user.id).all()
    return render_template('user/dashboard.html', consignments=consignments)

@app.route('/user/submit', methods=['GET', 'POST'])
@login_required
def submit_issue():
    if current_user.role != 'user':
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        department_id = request.form.get('department_id')
        
        attachment_url = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    attachment_url = upload_result.get('secure_url')
                except Exception as e:
                    flash(f'File upload failed: {str(e)}', 'danger')
        
        tracking_id = "CCN" + str(uuid.uuid4().int)[:9] # Generate a simple tracking ID
        new_con = Consignment(title=title, description=description, tracking_id=tracking_id, 
                              user_id=current_user.id, department_id=department_id, attachment_url=attachment_url)
        db.session.add(new_con)
        db.session.commit()
        flash(f'Application submitted successfully! Your tracking ID is {tracking_id}', 'success')
        return redirect(url_for('user_dashboard'))
    
    departments = Department.query.all()
    return render_template('user/submit.html', departments=departments)

# --- Admin Routes ---
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    
    query = Consignment.query.filter_by(assigned_admin_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    consignments = query.order_by(Consignment.created_at.desc()).all()
    
    # Python-level date filtering if date_filter is provided (format: YYYY-MM-DD)
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            consignments = [con for con in consignments if con.created_at and con.created_at.date() == filter_date]
        except ValueError:
            pass

    return render_template('admin/dashboard.html', consignments=consignments, status_filter=status_filter, date_filter=date_filter)

@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        new_password = request.form.get('password')
        if new_password:
            current_user.set_password(new_password)
            db.session.commit()
            flash(_('Password updated successfully.), '), ')')
            return redirect(url_for('admin_profile'))
    return render_template('admin/profile.html')

@app.route('/admin/contact')
@login_required
def admin_contact():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('admin/contact.html')

@app.route('/admin/create_application', methods=['GET', 'POST'])
@login_required
def admin_create_application():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        department_id = request.form.get('department_id')
        
        phone_no = request.form.get('phone_no')
        name = request.form.get('name')
        address = request.form.get('address')
        place = request.form.get('place')
        district = request.form.get('district')
        
        user = None
        if phone_no:
            user = User.query.filter_by(phone_no=phone_no).first()
            if not user:
                username = phone_no
                user = User(username=username, role='user', name=name, address=address, phone_no=phone_no, place=place, district=district)
                user.set_password(phone_no)
                db.session.add(user)
                db.session.flush()
                flash(_('New user account created automatically.), '), ')')
        
        user_id = user.id if user else current_user.id
        
        attachment_url = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    attachment_url = upload_result.get('secure_url')
                except Exception as e:
                    flash(f'File upload failed: {str(e)}', 'danger')
        
        tracking_id = "CCN" + str(uuid.uuid4().int)[:9]
        new_con = Consignment(title=title, description=description, tracking_id=tracking_id, 
                              user_id=user_id, department_id=department_id, attachment_url=attachment_url)
        db.session.add(new_con)
        db.session.commit()
        flash(f'Application submitted successfully! Tracking ID: {tracking_id}', 'success')
        return redirect(url_for('admin_dashboard'))
    
    departments = Department.query.all()
    return render_template('admin/create_application.html', departments=departments)

@app.route('/admin/update_status/<int:id>', methods=['POST'])
@login_required
def admin_update_status(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(id)
    if consignment.assigned_admin_id != current_user.id:
        flash(_('Not authorized.), '), ')')
        return redirect(url_for('admin_dashboard'))
    
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Under Review', 'Approved', 'Completed', 'Closed']:
        consignment.status = new_status
        db.session.commit()
        flash(_('Status updated.), '), ')')
    return redirect(url_for('admin_dashboard'))

# --- SuperAdmin Routes ---
@app.route('/superadmin/dashboard')
@login_required
def superadmin_dashboard():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    
    # Ensure a SystemBalance row exists
    balance = SystemBalance.query.order_by(SystemBalance.id.asc()).first()
    if not balance:
        balance = SystemBalance(total_balance=200000.0, current_balance=150000.0, used_up_balance=50000.0)
        db.session.add(balance)
        db.session.commit()
    
    stats = {
        'total_apps': Consignment.query.count(),
        'pending_apps': Consignment.query.filter_by(status='Pending').count(),
        'approved_apps': Consignment.query.filter_by(status='Approved').count(),
        'completed_apps': Consignment.query.filter_by(status='Completed').count(),
        'total_users': User.query.filter_by(role='user').count(),
        'total_admins': User.query.filter(User.role.in_(['admin', 'superadmin'])).count()
    }
    
    return render_template('superadmin/dashboard.html', stats=stats, balance=balance)

@app.route('/superadmin/update_balance', methods=['POST'])
@login_required
def superadmin_update_balance():
    if current_user.role != 'superadmin':
        return {"status": "error", "message": "Unauthorized"}, 403
        
    balance = SystemBalance.query.order_by(SystemBalance.id.asc()).first()
    if not balance:
        balance = SystemBalance()
        db.session.add(balance)
        
    try:
        data = request.get_json()
        if not data:
            return {"status": "error", "message": "Invalid data"}, 400
            
        if 'total_balance' in data:
            balance.total_balance = float(data['total_balance'])
        if 'current_balance' in data:
            balance.current_balance = float(data['current_balance'])
            
        balance.used_up_balance = balance.total_balance - balance.current_balance
            
        db.session.commit()
        flash(_('Balance updated successfully.'))
        return {"status": "success", "message": "Balance updated successfully"}
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}, 500

@app.route('/superadmin/applications')
@login_required
def superadmin_applications():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    search_query = request.args.get('search', '').strip()
    
    query = Consignment.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    consignments = query.order_by(Consignment.created_at.desc()).all()
    
    if search_query:
        filtered_consignments = []
        for con in consignments:
            match = False
            if search_query.lower() in con.tracking_id.lower() or (con.title and search_query.lower() in con.title.lower()):
                match = True
            elif con.submitter:
                if con.submitter.phone_no and search_query in con.submitter.phone_no:
                    match = True
                elif con.submitter.username and search_query.lower() in con.submitter.username.lower():
                    match = True
                elif con.submitter.name and search_query.lower() in con.submitter.name.lower():
                    match = True
            if match:
                filtered_consignments.append(con)
        consignments = filtered_consignments

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            consignments = [con for con in consignments if con.created_at and con.created_at.date() == filter_date]
        except ValueError:
            pass
            
    admins = User.query.filter_by(role='admin').all()
    
    return render_template('superadmin/applications.html', consignments=consignments, admins=admins, status_filter=status_filter, date_filter=date_filter, search_query=search_query)

@app.route('/superadmin/users', methods=['GET', 'POST'])
@login_required
def superadmin_users():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        department_id = request.form.get('department_id') or None
        
        if User.query.filter_by(username=username).first():
            flash(_('Username already exists.'), 'danger')
        else:
            new_user = User(username=username, role=role, department_id=department_id)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(_('User created successfully.'), 'success')
        return redirect(url_for('superadmin_users'))
        
    query = User.query
    if search_query:
        query = query.filter(db.or_(
            User.username.ilike(f'%{search_query}%'),
            User.name.ilike(f'%{search_query}%'),
            User.phone_no.ilike(f'%{search_query}%')
        ))
    users = query.all()
    departments = Department.query.all()
    return render_template('superadmin/users.html', users=users, departments=departments, search_query=search_query)

@app.route('/superadmin/edit_user/<int:user_id>', methods=['POST'])
@login_required
def superadmin_edit_user(user_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
        
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('password')
    department_id = request.form.get('department_id') or None
    
    if new_password:
        user.set_password(new_password)
    user.department_id = department_id
    db.session.commit()
    flash(f'User {user.username} updated successfully.', 'success')
    return redirect(url_for('superadmin_users'))

@app.route('/superadmin/departments', methods=['GET', 'POST'])
@login_required
def superadmin_departments():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        officer_name = request.form.get('officer_name')
        officer_phone = request.form.get('officer_phone')
        officer_email = request.form.get('officer_email')
        if Department.query.filter_by(name=name).first():
            flash(_('Department already exists.'), 'danger')
        else:
            new_dept = Department(name=name, officer_name=officer_name, officer_phone=officer_phone, officer_email=officer_email)
            db.session.add(new_dept)
            db.session.commit()
            flash(_('Department created successfully.'), 'success')
        return redirect(url_for('superadmin_departments'))
        
    departments = Department.query.all()
    return render_template('superadmin/departments.html', departments=departments)

@app.route('/superadmin/delete_department/<int:dept_id>', methods=['POST'])
@login_required
def superadmin_delete_department(dept_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    dept = Department.query.get_or_404(dept_id)
    User.query.filter_by(department_id=dept.id).update({User.department_id: None})
    Consignment.query.filter_by(department_id=dept.id).update({Consignment.department_id: None})
    db.session.delete(dept)
    db.session.commit()
    flash(_('Department deleted successfully.'), 'success')
    return redirect(url_for('superadmin_departments'))

@app.route('/superadmin/user/<int:user_id>')
@login_required
def superadmin_user_profile(user_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    return render_template('superadmin/user_profile.html', user=user)

@app.route('/superadmin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def superadmin_delete_user(user_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    if current_user.id == user_id:
        flash(_('You cannot delete your own profile.'), 'danger')
        return redirect(url_for('superadmin_users'))
    user = User.query.get_or_404(user_id)
    Consignment.query.filter_by(user_id=user.id).update({Consignment.user_id: None})
    Consignment.query.filter_by(assigned_admin_id=user.id).update({Consignment.assigned_admin_id: None})
    db.session.delete(user)
    db.session.commit()
    flash(_('User deleted successfully.'), 'success')
    return redirect(url_for('superadmin_users'))

@app.route('/superadmin/delete_application/<int:con_id>', methods=['POST'])
@login_required
def superadmin_delete_application(con_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(con_id)
    db.session.delete(consignment)
    db.session.commit()
    flash(_('Application deleted successfully.'), 'success')
    return redirect(url_for('superadmin_dashboard'))

@app.route('/superadmin/edit_application/<int:con_id>', methods=['GET', 'POST'])
@login_required
def superadmin_edit_application(con_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(con_id)
    if request.method == 'POST':
        consignment.title = request.form.get('title')
        consignment.description = request.form.get('description')
        db.session.commit()
        flash(_('Application updated successfully.'), 'success')
        return redirect(url_for('superadmin_dashboard'))
    return render_template('superadmin/edit_application.html', consignment=consignment)

@app.route('/superadmin/view_application/<int:con_id>')
@login_required
def superadmin_view_application(con_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(con_id)
    return render_template('superadmin/view_application.html', consignment=consignment)

@app.route('/superadmin/export/csv')
@login_required
def superadmin_export_csv():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignments = Consignment.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Tracking ID', 'Title', 'Description', 'Status', 'User Name', 'User Phone', 'Department', 'Created At'])
    for c in consignments:
        user_name = c.submitter.name if c.submitter else 'N/A'
        user_phone = c.submitter.phone_no if c.submitter else 'N/A'
        dept_name = c.department.name if c.department else 'N/A'
        writer.writerow([c.id, c.tracking_id, c.title, c.description, c.status, user_name, user_phone, dept_name, c.created_at])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=applications.csv"}
    )

@app.route('/superadmin/export/xml')
@login_required
def superadmin_export_xml():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignments = Consignment.query.all()
    
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n<Applications>\n'
    for c in consignments:
        user_name = c.submitter.name if c.submitter else 'N/A'
        user_phone = c.submitter.phone_no if c.submitter else 'N/A'
        dept_name = c.department.name if c.department else 'N/A'
        xml_data += f'''  <Application>
    <ID>{c.id}</ID>
    <TrackingID>{c.tracking_id}</TrackingID>
    <Title>{c.title}</Title>
    <Status>{c.status}</Status>
    <UserName>{user_name}</UserName>
    <UserPhone>{user_phone}</UserPhone>
    <Department>{dept_name}</Department>
  </Application>\n'''
    xml_data += '</Applications>'
    
    return Response(
        xml_data,
        mimetype="application/xml",
        headers={"Content-disposition": "attachment; filename=applications.xml"}
    )

@app.route('/superadmin/assign/<int:con_id>', methods=['POST'])
@login_required
def superadmin_assign(con_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(con_id)
    admin_id = request.form.get('admin_id')
    if admin_id:
        consignment.assigned_admin_id = admin_id
        db.session.commit()
        flash(_('Admin assigned successfully.'))
    return redirect(url_for('superadmin_dashboard'))

from flask import send_file
from openpyxl import Workbook
from io import BytesIO

@app.route('/pending-works', methods=['GET'])
@login_required
def pending_works():
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status', '')
    local_body_filter = request.args.get('local_body', '')
    ward_filter = request.args.get('ward_no', '')
    amount_min = request.args.get('amount_min', '')
    amount_max = request.args.get('amount_max', '')
    
    query = PendingWork.query
    if status_filter:
        query = query.filter(PendingWork.status == status_filter)
    if local_body_filter:
        query = query.filter(PendingWork.local_body.ilike(f"%{local_body_filter}%"))
    if ward_filter:
        try:
            query = query.filter(PendingWork.ward_no == int(ward_filter))
        except ValueError:
            pass
    if amount_min:
        try:
            query = query.filter(PendingWork.amount >= int(amount_min))
        except ValueError:
            pass
    if amount_max:
        try:
            query = query.filter(PendingWork.amount <= int(amount_max))
        except ValueError:
            pass
            
    works = query.all()
    base_template = 'dash_base_admin.html' if current_user.role == 'superadmin' else 'dash_base.html'
    return render_template('admin/pending_works.html', works=works, 
                           status_filter=status_filter, local_body_filter=local_body_filter,
                           ward_filter=ward_filter, amount_min=amount_min, amount_max=amount_max,
                           base_template=base_template)

@app.route('/pending-works/add', methods=['POST'])
@login_required
def add_pending_work():
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
        
    try:
        work_name = request.form.get('work_name')
        amount = int(request.form.get('amount', 0))
        local_body = request.form.get('local_body')
        ward_no = int(request.form.get('ward_no', 0))
        status = request.form.get('status', 'Pending')
        
        work = PendingWork(
            work_name=work_name,
            amount=amount,
            local_body=local_body,
            ward_no=ward_no,
            status=status
        )
        db.session.add(work)
        db.session.commit()
        flash(_('Pending Work added successfully.'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding work: {str(e)}', 'danger')
        
    return redirect(url_for('pending_works'))

@app.route('/pending-works/edit/<int:work_id>', methods=['POST'])
@login_required
def edit_pending_work(work_id):
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
        
    work = PendingWork.query.get_or_404(work_id)
    try:
        work.work_name = request.form.get('work_name')
        work.amount = int(request.form.get('amount', 0))
        work.local_body = request.form.get('local_body')
        work.ward_no = int(request.form.get('ward_no', 0))
        work.status = request.form.get('status')
        
        db.session.commit()
        flash(_('Pending Work updated successfully.'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating work: {str(e)}', 'danger')
        
    return redirect(url_for('pending_works'))

@app.route('/pending-works/download', methods=['GET'])
@login_required
def download_pending_works():
    if current_user.role != 'superadmin':
        flash(_('Unauthorized access.'), 'danger')
        return redirect(url_for('index'))
        
    status_filter = request.args.get('status', '')
    local_body_filter = request.args.get('local_body', '')
    ward_filter = request.args.get('ward_no', '')
    amount_min = request.args.get('amount_min', '')
    amount_max = request.args.get('amount_max', '')
    
    query = PendingWork.query
    if status_filter:
        query = query.filter(PendingWork.status == status_filter)
    if local_body_filter:
        query = query.filter(PendingWork.local_body.ilike(f"%{local_body_filter}%"))
    if ward_filter:
        try:
            query = query.filter(PendingWork.ward_no == int(ward_filter))
        except ValueError:
            pass
    if amount_min:
        try:
            query = query.filter(PendingWork.amount >= int(amount_min))
        except ValueError:
            pass
    if amount_max:
        try:
            query = query.filter(PendingWork.amount <= int(amount_max))
        except ValueError:
            pass
            
    works = query.all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Pending Works"
    
    headers = ["SR (ID)", "Work Name", "Amount", "Local Body", "Ward No", "Status"]
    ws.append(headers)
    
    for idx, w in enumerate(works, start=1):
        ws.append([idx, w.work_name, w.amount, w.local_body, w.ward_no, w.status])
        
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    filename = f"pending_works_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        file_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/vehicles', methods=['GET'])
@login_required
def vehicles():
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
        
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('vehicle_type', '')
    
    query = Vehicle.query
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if type_filter:
        query = query.filter(Vehicle.vehicle_type == type_filter)
        
    vehicles_list = query.all()
    base_template = 'dash_base_admin.html' if current_user.role == 'superadmin' else 'dash_base.html'
    return render_template('admin/vehicles.html', vehicles=vehicles_list, 
                           status_filter=status_filter, type_filter=type_filter,
                           base_template=base_template)

@app.route('/vehicles/add', methods=['POST'])
@login_required
def add_vehicle():
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
        
    try:
        vehicle_number = request.form.get('vehicle_number')
        vehicle_model = request.form.get('vehicle_model')
        vehicle_year = int(request.form.get('vehicle_year', 0))
        driver_name = request.form.get('driver_name')
        driver_contract = request.form.get('driver_contract')
        driver_license = request.form.get('driver_license')
        vehicle_type = request.form.get('vehicle_type', 'owned')
        status = request.form.get('status', 'Pending')
        
        veh = Vehicle(
            vehicle_number=vehicle_number,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
            driver_name=driver_name,
            driver_contract=driver_contract,
            driver_license=driver_license,
            vehicle_type=vehicle_type,
            status=status
        )
        db.session.add(veh)
        db.session.commit()
        flash(_('Vehicle added successfully.'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding vehicle: {str(e)}', 'danger')
        
    return redirect(url_for('vehicles'))

@app.route('/vehicles/edit/<int:veh_id>', methods=['POST'])
@login_required
def edit_vehicle(veh_id):
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('index'))
        
    veh = Vehicle.query.get_or_404(veh_id)
    try:
        veh.vehicle_number = request.form.get('vehicle_number')
        veh.vehicle_model = request.form.get('vehicle_model')
        veh.vehicle_year = int(request.form.get('vehicle_year', 0))
        veh.driver_name = request.form.get('driver_name')
        veh.driver_contract = request.form.get('driver_contract')
        veh.driver_license = request.form.get('driver_license')
        veh.vehicle_type = request.form.get('vehicle_type')
        veh.status = request.form.get('status')
        
        db.session.commit()
        flash(_('Vehicle updated successfully.'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating vehicle: {str(e)}', 'danger')
        
    return redirect(url_for('vehicles'))

# --- Setup Script ---
@app.cli.command("init-db")
def init_db():
    db.create_all()
    # Create super admin
    if not User.query.filter_by(username='superadmin').first():
        sa = User(username='superadmin', role='superadmin')
        sa.set_password('admin123')
        db.session.add(sa)
    # Create some departments
    if not Department.query.first():
        for d in ['IT', 'HR', 'Finance', 'Operations']:
            db.session.add(Department(name=d))
    db.session.commit()
    print("Database initialized.")

if __name__ == '__main__':
    print("DB URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    app.run(debug=True)
