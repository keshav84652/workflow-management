"""
Authentication and session management blueprint
"""

from flask import Blueprint, render_template, redirect, url_for, request, session, flash, make_response, jsonify
from datetime import datetime
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Firm, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def home():
    # Show simplified landing page as main entry point
    return render_template('auth/landing.html')


@auth_bp.route('/landing')
def landing():
    # Redirect to main landing page for consistency
    return redirect(url_for('auth.home'))


@auth_bp.route('/login')
def login():
    if 'firm_id' in session:
        if 'user_id' in session:
            return redirect(url_for('dashboard.main'))
        else:
            return redirect(url_for('auth.select_user'))
    return render_template('auth/login.html')


@auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    access_code = request.form.get('access_code', '').strip()
    email = request.form.get('email', '').strip()
    
    firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
    
    if firm:
        # Make session permanent for better persistence
        session.permanent = True
        
        # Store email in session for tracking
        session['user_email'] = email
        session['firm_id'] = firm.id
        session['firm_name'] = firm.name
        
        # For demo access, store email in database for tracking
        if access_code == 'DEMO2024':
            try:
                # Check if email already exists for demo access
                existing_request = db.session.execute(
                    db.text("SELECT * FROM demo_access_request WHERE email = :email AND firm_access_code = 'DEMO2024'"),
                    {'email': email}
                ).first()
                
                if not existing_request:
                    # Create new demo access record
                    db.session.execute(
                        db.text("""
                            INSERT INTO demo_access_request 
                            (email, firm_access_code, ip_address, user_agent, granted, granted_at, created_at) 
                            VALUES (:email, 'DEMO2024', :ip_address, :user_agent, 1, :granted_at, :created_at)
                        """),
                        {
                            'email': email,
                            'ip_address': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'granted_at': datetime.utcnow(),
                            'created_at': datetime.utcnow()
                        }
                    )
                    db.session.commit()
            except Exception as e:
                # Don't block access if demo tracking fails
                print(f"Demo tracking error: {e}")
                pass
        
        return redirect(url_for('auth.select_user'))
    else:
        flash('Invalid access code', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/select-user')
def select_user():
    if 'firm_id' not in session:
        return redirect(url_for('auth.login'))
    
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('auth/select_user.html', users=users, firm_name=session.get('firm_name', 'Your Firm'))


@auth_bp.route('/set-user', methods=['POST'])
def set_user():
    if 'firm_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = request.form.get('user_id')
    user = User.query.filter_by(id=user_id, firm_id=session['firm_id']).first()
    
    if user:
        # Ensure session remains permanent
        session.permanent = True
        
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        flash(f'Welcome, {user.name}!', 'success')
        return redirect(url_for('dashboard.main'))
    else:
        flash('Invalid user selection', 'error')
        return redirect(url_for('auth.select_user'))


@auth_bp.route('/switch-user')
def switch_user():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    return redirect(url_for('auth.select_user'))


@auth_bp.route('/logout')
def logout():
    """Logout user with proper cache control and session clearing"""
    session.clear()
    
    # Create response with proper cache control headers
    response = make_response(redirect(url_for('auth.home')))
    
    # Prevent caching of any authenticated content
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    # Clear any authentication cookies if they exist
    response.set_cookie('session', '', expires=0)
    
    return response


@auth_bp.route('/clear-session')
def clear_session():
    """Clear session and redirect to landing page with proper cache control"""
    session.clear()
    
    response = make_response(redirect(url_for('auth.home')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@auth_bp.route('/api/auth-status')
def auth_status():
    """API endpoint to check authentication status"""
    is_authenticated = 'firm_id' in session and 'user_id' in session
    
    response_data = {
        'authenticated': is_authenticated,
        'firm_id': session.get('firm_id'),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    response = make_response(jsonify(response_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response