"""
Authentication and session management blueprint
"""

from flask import Blueprint, render_template, redirect, url_for, request, session, flash, make_response, jsonify
from datetime import datetime
from src.shared.database.db_import import db
from .service import AuthService

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
    if AuthService.is_authenticated():
        return redirect(url_for('dashboard.main'))
    elif AuthService.is_firm_authenticated():
        return redirect(url_for('auth.select_user'))
    return render_template('auth/login.html')


@auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    access_code = request.form.get('access_code', '').strip()
    email = request.form.get('email', '').strip()
    
    # Use AuthService for authentication
    auth_service = AuthService()
    result = auth_service.authenticate_firm(access_code, email)
    
    if result['success']:
        # Create session using AuthService
        auth_service.create_session(result['firm'], email)
        return redirect(url_for('auth.select_user'))
    else:
        flash(result['message'], 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/select-user')
def select_user():
    if not AuthService.is_firm_authenticated():
        return redirect(url_for('auth.login'))
    
    firm_id = session['firm_id']
    # Use AuthService to get users
    auth_service = AuthService()
    users = auth_service.get_users_for_firm(firm_id)
    return render_template('auth/select_user.html', users=users, firm_name=session.get('firm_name', 'Your Firm'))


@auth_bp.route('/set-user', methods=['POST'])
def set_user():
    if not AuthService.is_firm_authenticated():
        return redirect(url_for('auth.login'))
    
    user_id = request.form.get('user_id')
    firm_id = session['firm_id']
    
    # Use AuthService to set user in session
    auth_service = AuthService()
    result = auth_service.set_user_in_session(int(user_id), firm_id)
    
    if result['success']:
        flash(f'Welcome, {result["user"]["name"]}!', 'success')
        return redirect(url_for('dashboard.main'))
    else:
        flash(result['message'], 'error')
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
    # Use AuthService for logout
    AuthService.logout()
    
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
    # Use AuthService for session clearing
    AuthService.logout()
    
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