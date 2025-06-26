"""
API endpoints blueprint

UPDATED: Modernized with standardized session management and clean imports.
"""

from flask import Blueprint, jsonify, request
from core.db_import import db
from models import Client, Project, Task
from services.base import SessionService

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/clients/search')
def search_clients():
    firm_id = SessionService.get_current_firm_id()
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
    
    # Check access permission using standardized session service
    current_firm_id = SessionService.get_current_firm_id()
    if project.firm_id != current_firm_id:
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
    firm_id = SessionService.get_current_firm_id()
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'entity_type': client.entity_type,
        'email': client.email,
        'phone': client.phone,
        'is_active': client.is_active
    } for client in clients])
