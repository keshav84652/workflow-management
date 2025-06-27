"""
Data export functionality blueprint
"""

from flask import Blueprint, jsonify, request, session, Response
from datetime import date
import csv
import io

from utils.session_helpers import get_session_firm_id, get_session_user_id
from services.export_service import ExportService

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/tasks')
def export_tasks():
    firm_id = get_session_firm_id()
    format_type = request.args.get('format', 'csv')
    
    # Use ExportService for business logic
    result = ExportService.get_tasks_for_export(firm_id)
    
    if not result['success']:
        return jsonify({'error': result['message']}), 500
    
    tasks = result['tasks']
    
    if format_type == 'csv':
        # Format data using service
        formatted_data = ExportService.format_task_export_data(tasks)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Task Title', 'Description', 'Status', 'Priority', 
            'Due Date', 'Estimated Hours', 'Actual Hours',
            'Assignee', 'Project', 'Client', 'Created Date'
        ])
        
        # Write data
        for data in formatted_data:
            writer.writerow([
                data['title'],
                data['description'],
                data['status'],
                data['priority'],
                data['due_date'],
                data['estimated_hours'],
                data['actual_hours'],
                data['assignee'],
                data['project'],
                data['client'],
                data['created_at']
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=tasks_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400


@export_bp.route('/projects')
def export_projects():
    firm_id = get_session_firm_id()
    format_type = request.args.get('format', 'csv')
    
    # Use ExportService for business logic
    result = ExportService.get_projects_for_export(firm_id)
    
    if not result['success']:
        return jsonify({'error': result['message']}), 500
    
    projects = result['projects']
    
    if format_type == 'csv':
        # Format data using service
        formatted_data = ExportService.format_project_export_data(projects)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Project Name', 'Client Name', 'Status', 'Priority',
            'Start Date', 'Due Date', 'Template', 'Progress %',
            'Total Tasks', 'Completed Tasks', 'Created Date'
        ])
        
        # Write data
        for data in formatted_data:
            writer.writerow([
                data['name'],
                data['client_name'],
                data['status'],
                data['priority'],
                data['start_date'],
                data['due_date'],
                data['template'],
                data['progress_percentage'],
                data['total_tasks'],
                data['completed_tasks'],
                data['created_at']
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=projects_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400


@export_bp.route('/clients')
def export_clients():
    firm_id = get_session_firm_id()
    format_type = request.args.get('format', 'csv')
    
    # Use ExportService for business logic
    result = ExportService.get_clients_for_export(firm_id)
    
    if not result['success']:
        return jsonify({'error': result['message']}), 500
    
    clients = result['clients']
    
    if format_type == 'csv':
        # Format data using service
        formatted_data = ExportService.format_client_export_data(clients)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Client Name', 'Entity Type', 'Email', 'Phone', 'Address',
            'Contact Person', 'Tax ID', 'Active Projects', 'Notes', 'Created Date'
        ])
        
        # Write data
        for data in formatted_data:
            writer.writerow([
                data['name'],
                data['entity_type'],
                data['email'],
                data['phone'],
                data['address'],
                data['contact_person'],
                data['tax_id'],
                data['active_projects'],
                data['notes'],
                data['created_at']
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=clients_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400