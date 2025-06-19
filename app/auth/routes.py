# Authentication Routes
# Enhanced authentication with role management, keeping access code approach

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

from app.auth.models import Firm, User, UserRole, ActivityLog
from app.auth.services import AuthService, UserService
from app.core.permissions import firm_required, requires_permission, EntityType
from app.core.models import Right
from app.core.extensions import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def landing():
    """Landing page"""
    return render_template('auth/landing.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Access code login"""
    if request.method == 'POST':
        access_code = request.form.get('access_code')
        
        # Use auth service for login logic
        auth_service = AuthService()
        result = auth_service.authenticate_firm(access_code)
        
        if result.is_success():
            session['firm_id'] = result.data.id
            session['access_code'] = access_code
            return redirect(url_for('auth.select_user'))
        else:
            flash('Invalid access code', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/select-user')
def select_user():
    """User selection after firm authentication"""
    firm_id = session.get('firm_id')
    if not firm_id:
        return redirect(url_for('auth.login'))
    
    users = User.query.filter_by(firm_id=firm_id, is_active=True).all()
    firm = Firm.query.get(firm_id)
    
    return render_template('auth/select_user.html', users=users, firm=firm)


@auth_bp.route('/set-user', methods=['POST'])
def set_user():
    """Set selected user in session"""
    firm_id = session.get('firm_id')
    user_id = request.form.get('user_id')
    
    if not firm_id or not user_id:
        flash('Invalid selection', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(id=user_id, firm_id=firm_id, is_active=True).first()
    if not user:
        flash('Invalid user selection', 'error')
        return redirect(url_for('auth.select_user'))
    
    # Set user session
    session['user_id'] = user.id
    session['user_role'] = user.role.value
    
    # Update last login
    user.last_login = datetime.utcnow()
    user.update_last_activity()
    
    # Log activity
    activity = ActivityLog(
        action='User Login',
        entity_type='user',
        entity_id=user.id,
        firm_id=firm_id,
        created_by_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(activity)
    db.session.commit()
    
    return redirect(url_for('reports.dashboard'))


@auth_bp.route('/switch-user')
@firm_required
def switch_user():
    """Switch to different user in same firm"""
    return redirect(url_for('auth.select_user'))


@auth_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.landing'))


# User Management Routes (Admin only)
@auth_bp.route('/users')
@requires_permission(EntityType.USER, Right.READ)
def list_users(current_user, firm_id):
    """List all users in firm"""
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('auth/users.html', users=users)


@auth_bp.route('/users/create', methods=['GET', 'POST'])
@requires_permission(EntityType.USER, Right.ADMIN)
def create_user(current_user, firm_id):
    """Create new user"""
    if request.method == 'POST':
        user_service = UserService(current_user)
        result = user_service.create_user(
            name=request.form.get('name'),
            email=request.form.get('email'),
            role=UserRole(request.form.get('role')),
            title=request.form.get('title'),
            department=request.form.get('department'),
            hourly_rate=request.form.get('hourly_rate'),
            firm_id=firm_id
        )
        
        if result.is_success():
            flash('User created successfully', 'success')
            return redirect(url_for('auth.list_users'))
        else:
            for field, errors in result.errors.items():
                flash(f'{field}: {errors}', 'error')
    
    roles = [(role.value, role.value) for role in UserRole]
    return render_template('auth/create_user.html', roles=roles)


@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@requires_permission(EntityType.USER, Right.WRITE)
def edit_user(user_id, current_user, entity):
    """Edit user details"""
    if request.method == 'POST':
        user_service = UserService(current_user)
        result = user_service.update_user(
            entity,
            name=request.form.get('name'),
            email=request.form.get('email'),
            role=UserRole(request.form.get('role')) if request.form.get('role') else None,
            title=request.form.get('title'),
            department=request.form.get('department'),
            hourly_rate=request.form.get('hourly_rate'),
            is_active=request.form.get('is_active') == 'on'
        )
        
        if result.is_success():
            flash('User updated successfully', 'success')
            return redirect(url_for('auth.list_users'))
        else:
            for field, errors in result.errors.items():
                flash(f'{field}: {errors}', 'error')
    
    roles = [(role.value, role.value) for role in UserRole]
    return render_template('auth/edit_user.html', user=entity, roles=roles)


@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@requires_permission(EntityType.USER, Right.ADMIN)
def toggle_user_status(user_id, current_user, entity):
    """Toggle user active status"""
    user_service = UserService(current_user)
    result = user_service.toggle_user_status(entity)
    
    if result.is_success():
        status = 'activated' if entity.is_active else 'deactivated'
        flash(f'User {status} successfully', 'success')
    else:
        flash('Error updating user status', 'error')
    
    return redirect(url_for('auth.list_users'))


# API endpoints for user management
@auth_bp.route('/api/users/search')
@requires_permission(EntityType.USER, Right.READ)
def api_search_users(current_user, firm_id):
    """Search users API endpoint"""
    query = request.args.get('q', '')
    
    users = User.query.filter_by(firm_id=firm_id, is_active=True)\
                     .filter(User.name.contains(query))\
                     .limit(10).all()
    
    return jsonify([{
        'id': user.id,
        'name': user.name,
        'role': user.role.value,
        'title': user.title
    } for user in users])


@auth_bp.route('/profile')
@firm_required
def profile(current_user):
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/profile/update', methods=['POST'])
@firm_required
def update_profile(current_user):
    """Update user profile"""
    user_service = UserService(current_user)
    result = user_service.update_profile(
        current_user,
        name=request.form.get('name'),
        email=request.form.get('email'),
        title=request.form.get('title'),
        preferences=request.form.to_dict()
    )
    
    if result.is_success():
        flash('Profile updated successfully', 'success')
    else:
        flash('Error updating profile', 'error')
    
    return redirect(url_for('auth.profile'))