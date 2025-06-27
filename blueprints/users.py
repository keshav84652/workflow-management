"""
User management blueprint

UPDATED: Now uses modern service infrastructure and standardized session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.db_import import db
from models import User
from services.base import SessionService

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
def list_users():
    from services.admin_service import AdminService
    
    # Use standardized session management
    firm_id = SessionService.get_current_firm_id()
    # Use UserService for getting users
    from services.user_service import UserService
    users = UserService.get_users_by_firm(firm_id)
    return render_template('admin/users.html', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        from services.admin_service import AdminService
        
        # Use standardized session management
        firm_id = SessionService.get_current_firm_id()
        name = request.form.get('name')
        role = request.form.get('role', 'Member')
        
        result = AdminService.create_user(name, role, firm_id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('users.list_users'))
    
    return render_template('admin/create_user.html')