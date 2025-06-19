"""
Administrative functions blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from core import db
from models import Firm, User, WorkType, TaskStatus

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
def login():
    return render_template('admin/admin_login.html')


@admin_bp.route('/authenticate', methods=['POST'])
def authenticate():
    password = request.form.get('password')
    # Simple admin authentication - in production use proper auth
    if password == 'admin123':  # This should be configurable
        session['admin_authenticated'] = True
        return redirect(url_for('admin.dashboard'))
    else:
        flash('Invalid admin password', 'error')
        return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin.login'))
    
    # Basic admin dashboard functionality would go here
    firms = Firm.query.all()
    return render_template('admin/admin_dashboard.html', firms=firms)


# Additional admin routes would be added here as needed
# For now, keeping it minimal to establish the pattern