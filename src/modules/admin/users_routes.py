"""
User management blueprint

UPDATED: Now uses modern service infrastructure and standardized session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.shared.database.db_import import db
from src.models import User
from src.shared.base import SessionService
from src.modules.admin.service import AdminService
from src.modules.admin.user_service import UserService

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
def list_users():
    # Use standardized session management
    firm_id = SessionService.get_current_firm_id()
    # Use UserService for getting users
    user_service = UserService()
    users = user_service.get_users_by_firm(firm_id)
    return render_template('admin/users.html', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        # Use standardized session management
        firm_id = SessionService.get_current_firm_id()
        created_by_user_id = SessionService.get_current_user_id()
        name = request.form.get('name')
        role = request.form.get('role', 'Member')
        
        user_service = UserService()
        result = user_service.create_user(name, role, firm_id, created_by_user_id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('users.list_users'))
    
    return render_template('admin/create_user.html')
