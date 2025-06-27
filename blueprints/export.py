"""
Data export functionality blueprint
"""

from flask import Blueprint, jsonify, request, session, Response
from datetime import date
import csv
import io

from core.db_import import db
from utils.session_helpers import get_session_firm_id, get_session_user_id
from models import Task, Project, Client

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/tasks')
def export_tasks():
    firm_id = get_session_firm_id()
    format_type = request.args.get('format', 'csv')
    
    # Get all tasks for the firm
    tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).all()
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Task Title', 'Description', 'Status', 'Priority', 
            'Due Date', 'Estimated Hours', 'Actual Hours',
            'Assignee', 'Project', 'Client', 'Created Date'
        ])
        
        # Write data
        for task in tasks:
            writer.writerow([
                task.title,
                task.description or '',
                task.status,
                task.priority,
                task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                task.estimated_hours or '',
                task.actual_hours or '',
                task.assignee.name if task.assignee else '',
                task.project.name if task.project else 'Independent Task',
                task.project.client_name if task.project else '',
                task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''
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
    
    # Get all projects for the firm
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Project Name', 'Client Name', 'Status', 'Priority',
            'Start Date', 'Due Date', 'Template', 'Progress %',
            'Total Tasks', 'Completed Tasks', 'Created Date'
        ])
        
        # Write data
        for project in projects:
            completed_tasks = len([t for t in project.tasks if t.status == 'Completed'])
            total_tasks = len(project.tasks)
            
            writer.writerow([
                project.name,
                project.client_name,
                project.status,
                project.priority if hasattr(project, 'priority') else 'Medium',
                project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                project.due_date.strftime('%Y-%m-%d') if project.due_date else '',
                project.template_origin.name if project.template_origin else '',
                f'{project.progress_percentage}%',
                total_tasks,
                completed_tasks,
                project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
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
    
    # Get all clients for the firm
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Client Name', 'Entity Type', 'Email', 'Phone', 'Address',
            'Contact Person', 'Tax ID', 'Active Projects', 'Notes', 'Created Date'
        ])
        
        # Write data
        for client in clients:
            active_projects = Project.query.filter_by(client_id=client.id, status='Active').count()
            
            writer.writerow([
                client.name,
                client.entity_type or '',
                client.email or '',
                client.phone or '',
                client.address or '',
                client.contact_person or '',
                client.tax_id or '',
                active_projects,
                client.notes or '',
                client.created_at.strftime('%Y-%m-%d %H:%M:%S') if client.created_at else ''
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=clients_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400