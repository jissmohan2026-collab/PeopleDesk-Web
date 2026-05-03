from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, bcrypt, User, Department, Consignment
import uuid

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
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, role='user')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('user_dashboard'))
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
        
        tracking_id = "CCN" + str(uuid.uuid4().int)[:9] # Generate a simple tracking ID
        new_con = Consignment(title=title, description=description, tracking_id=tracking_id, 
                              user_id=current_user.id, department_id=department_id)
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
    consignments = Consignment.query.filter_by(assigned_admin_id=current_user.id).all()
    return render_template('admin/dashboard.html', consignments=consignments)

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
    consignments = Consignment.query.all()
    admins = User.query.filter_by(role='admin').all()
    return render_template('superadmin/dashboard.html', consignments=consignments, admins=admins)

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

@app.route('/superadmin/create_admin', methods=['POST'])
@login_required
def superadmin_create_admin():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    username = request.form.get('username')
    password = request.form.get('password')
    department_id = request.form.get('department_id')
    
    if User.query.filter_by(username=username).first():
        flash('Admin username already exists.', 'danger')
    else:
        new_admin = User(username=username, role='admin', department_id=department_id)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        flash('Admin created successfully.', 'success')
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
    app.run()
