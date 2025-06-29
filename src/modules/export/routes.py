"""
Export routes for data export functionality
"""

from flask import Blueprint, jsonify, request, make_response, session
import csv
import io
from datetime import datetime

from src.shared.utils.consolidated import get_session_firm_id, get_session_user_id

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/projects/<format>')
def export_projects(format):
    """Export projects in specified format"""
    firm_id = get_session_firm_id()
    
    if format.lower() == 'csv':
        return _export_projects_csv(firm_id)
    elif format.lower() == 'json':
        return _export_projects_json(firm_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400


@export_bp.route('/clients/<format>')
def export_clients(format):
    """Export clients in specified format"""
    firm_id = get_session_firm_id()
    
    if format.lower() == 'csv':
        return _export_clients_csv(firm_id)
    elif format.lower() == 'json':
        return _export_clients_json(firm_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400


@export_bp.route('/tasks/<format>')
def export_tasks(format):
    """Export tasks in specified format"""
    firm_id = get_session_firm_id()
    
    if format.lower() == 'csv':
        return _export_tasks_csv(firm_id)
    elif format.lower() == 'json':
        return _export_tasks_json(firm_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400


def _export_projects_csv(firm_id):
    """Export projects as CSV"""
    try:
        from src.modules.project.service import ProjectService
        
        project_service = ProjectService()
        result = project_service.get_projects_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        projects = result['projects']
        
        # Create CSV output
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Description', 'Status', 'Start Date', 'End Date', 'Client', 'Created At'])
        
        # Write data
        for project in projects:
            writer.writerow([
                project.get('id', ''),
                project.get('name', ''),
                project.get('description', ''),
                project.get('status', ''),
                project.get('start_date', ''),
                project.get('end_date', ''),
                project.get('client_name', ''),
                project.get('created_at', '')
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=projects_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _export_projects_json(firm_id):
    """Export projects as JSON"""
    try:
        from src.modules.project.service import ProjectService
        
        project_service = ProjectService()
        result = project_service.get_projects_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        response_data = {
            'export_date': datetime.now().isoformat(),
            'firm_id': firm_id,
            'projects': result['projects']
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Content-Disposition'] = f'attachment; filename=projects_export_{datetime.now().strftime("%Y%m%d")}.json'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _export_clients_csv(firm_id):
    """Export clients as CSV"""
    try:
        from src.modules.client.service import ClientService
        
        client_service = ClientService()
        result = client_service.get_clients_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        clients = result['clients']
        
        # Create CSV output
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Address', 'Status', 'Created At'])
        
        # Write data
        for client in clients:
            writer.writerow([
                client.get('id', ''),
                client.get('name', ''),
                client.get('email', ''),
                client.get('phone', ''),
                client.get('address', ''),
                client.get('status', ''),
                client.get('created_at', '')
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _export_clients_json(firm_id):
    """Export clients as JSON"""
    try:
        from src.modules.client.service import ClientService
        
        client_service = ClientService()
        result = client_service.get_clients_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        response_data = {
            'export_date': datetime.now().isoformat(),
            'firm_id': firm_id,
            'clients': result['clients']
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d")}.json'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _export_tasks_csv(firm_id):
    """Export tasks as CSV"""
    try:
        from src.modules.project.task_service import TaskService
        
        task_service = TaskService()
        result = task_service.get_tasks_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        tasks = result['tasks']
        
        # Create CSV output
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Title', 'Description', 'Status', 'Priority', 'Due Date', 'Project', 'Assignee', 'Created At'])
        
        # Write data
        for task in tasks:
            writer.writerow([
                task.get('id', ''),
                task.get('title', ''),
                task.get('description', ''),
                task.get('status', ''),
                task.get('priority', ''),
                task.get('due_date', ''),
                task.get('project_name', ''),
                task.get('assignee_name', ''),
                task.get('created_at', '')
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _export_tasks_json(firm_id):
    """Export tasks as JSON"""
    try:
        from src.modules.project.task_service import TaskService
        
        task_service = TaskService()
        result = task_service.get_tasks_by_firm(firm_id)
        
        if not result['success']:
            return jsonify({'error': result['message']}), 500
        
        response_data = {
            'export_date': datetime.now().isoformat(),
            'firm_id': firm_id,
            'tasks': result['tasks']
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Content-Disposition'] = f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.json'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500