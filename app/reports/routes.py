# Reports Routes - Placeholder
from flask import Blueprint, render_template

from app.core.permissions import firm_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/dashboard')
@firm_required  
def dashboard(current_user, firm_id):
    """Dashboard placeholder"""
    return render_template('reports/dashboard.html', user=current_user)