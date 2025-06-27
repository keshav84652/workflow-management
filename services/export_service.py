"""
ExportService: Handles all business logic for data export operations.
"""

from core.db_import import db
from models import Task, Project, Client


class ExportService:
    @staticmethod
    def get_tasks_for_export(firm_id, filters=None):
        """Get all tasks for export with proper firm access control"""
        try:
            # Get all tasks for the firm using proper joins
            tasks = Task.query.outerjoin(Project).filter(
                db.or_(
                    Project.firm_id == firm_id,
                    db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
                )
            ).all()
            
            return {
                'success': True,
                'tasks': tasks
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving tasks for export: {str(e)}'
            }
    
    @staticmethod 
    def get_projects_for_export(firm_id, filters=None):
        """Get all projects for export with proper firm access control"""
        try:
            projects = Project.query.filter_by(firm_id=firm_id).all()
            
            return {
                'success': True,
                'projects': projects
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving projects for export: {str(e)}'
            }
    
    @staticmethod
    def get_clients_for_export(firm_id, filters=None):
        """Get all clients for export with proper firm access control"""
        try:
            clients = Client.query.filter_by(firm_id=firm_id).all()
            
            return {
                'success': True,
                'clients': clients
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving clients for export: {str(e)}'
            }
    
    @staticmethod
    def format_task_export_data(tasks):
        """Format task data for CSV export"""
        formatted_data = []
        
        for task in tasks:
            formatted_data.append({
                'title': task.title,
                'description': task.description or '',
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                'estimated_hours': task.estimated_hours or '',
                'actual_hours': task.actual_hours or '',
                'assignee': task.assignee.name if task.assignee else '',
                'project': task.project.name if task.project else 'Independent Task',
                'client': task.project.client_name if task.project else '',
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''
            })
        
        return formatted_data
    
    @staticmethod
    def format_project_export_data(projects):
        """Format project data for CSV export"""
        formatted_data = []
        
        for project in projects:
            completed_tasks = len([t for t in project.tasks if t.status == 'Completed'])
            total_tasks = len(project.tasks)
            
            formatted_data.append({
                'name': project.name,
                'client_name': project.client_name,
                'status': project.status,
                'priority': project.priority if hasattr(project, 'priority') else 'Medium',
                'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                'due_date': project.due_date.strftime('%Y-%m-%d') if project.due_date else '',
                'template': project.template_origin.name if project.template_origin else '',
                'progress_percentage': f'{project.progress_percentage}%',
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
            })
        
        return formatted_data
    
    @staticmethod
    def format_client_export_data(clients):
        """Format client data for CSV export"""
        formatted_data = []
        
        for client in clients:
            # Count active projects for this client
            active_projects = Project.query.filter_by(client_id=client.id, status='Active').count()
            
            formatted_data.append({
                'name': client.name,
                'entity_type': client.entity_type or '',
                'email': client.email or '',
                'phone': client.phone or '',
                'address': client.address or '',
                'contact_person': client.contact_person or '',
                'tax_id': client.tax_id or '',
                'active_projects': active_projects,
                'notes': client.notes or '',
                'created_at': client.created_at.strftime('%Y-%m-%d %H:%M:%S') if client.created_at else ''
            })
        
        return formatted_data