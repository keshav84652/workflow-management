"""
API endpoints blueprint
"""

from flask import Blueprint, jsonify, request, session
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Client, Project, Task

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/clients/search')
def search_clients():
    firm_id = session['firm_id']
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])
    
    clients = Client.query.filter(
        Client.firm_id == firm_id,
        Client.name.contains(query)
    ).limit(10).all()
    
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'entity_type': client.entity_type
    } for client in clients])


@api_bp.route('/project/<int:project_id>/progress', methods=['GET'])
def get_project_progress(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check access permission
    if project.firm_id != session['firm_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Calculate progress
    total_tasks = Task.query.filter_by(project_id=project_id).count()
    completed_tasks = Task.query.filter_by(project_id=project_id, status='Completed').count()
    
    progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return jsonify({
        'project_id': project.id,
        'project_name': project.name,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress_percentage': round(progress_percentage, 1)
    })


@api_bp.route('/clients')
def api_clients():
    firm_id = session['firm_id']
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'entity_type': client.entity_type,
        'email': client.email,
        'phone': client.phone,
        'is_active': client.is_active
    } for client in clients])
