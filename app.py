


from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, bcrypt, User, Department, Consignment
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
            flash('No consignment found with that tracking ID.', 'danger')
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
                flash('Username already exists.', 'danger')
                return redirect(url_for('register'))
            if phone_no and User.query.filter_by(phone_no=phone_no).first():
                flash('Phone number already registered.', 'danger')
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
            flash('Password updated successfully.', 'success')
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
                flash('New user account created automatically.', 'info')
        
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
        flash('Not authorized.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Under Review', 'Approved', 'Completed', 'Closed']:
        consignment.status = new_status
        db.session.commit()
        flash('Status updated.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- SuperAdmin Routes ---
@app.route('/superadmin/dashboard')
@login_required
def superadmin_dashboard():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    
    query = Consignment.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    consignments = query.order_by(Consignment.created_at.desc()).all()
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            consignments = [con for con in consignments if con.created_at and con.created_at.date() == filter_date]
        except ValueError:
            pass
            
    admins = User.query.filter_by(role='admin').all()
    return render_template('superadmin/dashboard.html', consignments=consignments, admins=admins, status_filter=status_filter, date_filter=date_filter)

@app.route('/superadmin/users', methods=['GET', 'POST'])
@login_required
def superadmin_users():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        department_id = request.form.get('department_id') or None
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            new_user = User(username=username, role=role, department_id=department_id)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully.', 'success')
        return redirect(url_for('superadmin_users'))
        
    users = User.query.all()
    departments = Department.query.all()
    return render_template('superadmin/users.html', users=users, departments=departments)

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
            flash('Department already exists.', 'danger')
        else:
            new_dept = Department(name=name, officer_name=officer_name, officer_phone=officer_phone, officer_email=officer_email)
            db.session.add(new_dept)
            db.session.commit()
            flash('Department created successfully.', 'success')
        return redirect(url_for('superadmin_departments'))
        
    departments = Department.query.all()
    return render_template('superadmin/departments.html', departments=departments)

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
        flash('You cannot delete your own profile.', 'danger')
        return redirect(url_for('superadmin_users'))
    user = User.query.get_or_404(user_id)
    Consignment.query.filter_by(user_id=user.id).update({Consignment.user_id: None})
    Consignment.query.filter_by(assigned_admin_id=user.id).update({Consignment.assigned_admin_id: None})
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('superadmin_users'))

@app.route('/superadmin/delete_application/<int:con_id>', methods=['POST'])
@login_required
def superadmin_delete_application(con_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    consignment = Consignment.query.get_or_404(con_id)
    db.session.delete(consignment)
    db.session.commit()
    flash('Application deleted successfully.', 'success')
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
        flash('Application updated successfully.', 'success')
        return redirect(url_for('superadmin_dashboard'))
    return render_template('superadmin/edit_application.html', consignment=consignment)

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
        flash('Admin assigned successfully.', 'success')
    return redirect(url_for('superadmin_dashboard'))

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
