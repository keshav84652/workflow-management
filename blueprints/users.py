"""
User management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import User

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
def list_users():
    from services.admin_service import AdminService
    
    firm_id = session['firm_id']
    # Note: AdminService doesn't have get_users_for_firm yet, using direct query for now
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('admin/users.html', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        from services.admin_service import AdminService
        
        firm_id = session['firm_id']
        name = request.form.get('name')
        role = request.form.get('role', 'Member')
        
        result = AdminService.create_user(name, role, firm_id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('users.list_users'))
    
    return render_template('admin/create_user.html')