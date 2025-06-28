"""
ExportService: Handles all business logic for data export operations.
"""

from core.db_import import db
from models import Task, Project, Client
from typing import List, Dict, Any, Callable


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
    def format_export_data(entities: List[Any], field_map: Dict[str, Any], 
                          custom_processors: Dict[str, Callable] = None) -> List[Dict[str, Any]]:
        """
        Generic utility to format entity data for CSV export.
        
        Args:
            entities: List of model objects to format
            field_map: Dictionary mapping output field names to model attributes or callable functions
            custom_processors: Optional dict of field-specific processing functions
            
        Returns:
            List of formatted dictionaries ready for CSV export
            
        Example:
            field_map = {
                'title': 'title',  # Direct attribute access
                'status': 'status',
                'due_date': lambda obj: obj.due_date.strftime('%Y-%m-%d') if obj.due_date else '',
                'assignee': lambda obj: obj.assignee.name if obj.assignee else ''
            }
        """
        formatted_data = []
        custom_processors = custom_processors or {}
        
        for entity in entities:
            row_data = {}
            
            for output_field, source in field_map.items():
                try:
                    # Apply custom processor if available
                    if output_field in custom_processors:
                        value = custom_processors[output_field](entity)
                    # Handle callable (lambda) sources
                    elif callable(source):
                        value = source(entity)
                    # Handle string attribute names
                    elif isinstance(source, str):
                        value = getattr(entity, source, '')
                        # Convert None to empty string
                        if value is None:
                            value = ''
                    else:
                        value = source  # Direct value
                    
                    row_data[output_field] = value
                    
                except Exception as e:
                    # Handle errors gracefully by using empty string
                    row_data[output_field] = ''
            
            formatted_data.append(row_data)
        
        return formatted_data
    
    @staticmethod
    def format_task_export_data(tasks):
        """Format task data for CSV export using generic formatter"""
        field_map = {
            'title': 'title',
            'description': lambda task: task.description or '',
            'status': 'status',
            'priority': 'priority',
            'due_date': lambda task: task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
            'estimated_hours': lambda task: task.estimated_hours or '',
            'actual_hours': lambda task: task.actual_hours or '',
            'assignee': lambda task: task.assignee.name if task.assignee else '',
            'project': lambda task: task.project.name if task.project else 'Independent Task',
            'client': lambda task: task.project.client_name if task.project else '',
            'created_at': lambda task: task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''
        }
        
        return ExportService.format_export_data(tasks, field_map)
    
    @staticmethod
    def format_project_export_data(projects):
        """Format project data for CSV export using generic formatter"""
        field_map = {
            'name': 'name',
            'client_name': 'client_name',
            'status': 'status',
            'priority': lambda project: getattr(project, 'priority', 'Medium'),
            'start_date': lambda project: project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            'due_date': lambda project: project.due_date.strftime('%Y-%m-%d') if project.due_date else '',
            'template': lambda project: project.template_origin.name if project.template_origin else '',
            'progress_percentage': lambda project: f'{project.progress_percentage}%',
            'total_tasks': lambda project: len(project.tasks),
            'completed_tasks': lambda project: len([t for t in project.tasks if t.status == 'Completed']),
            'created_at': lambda project: project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
        }
        
        return ExportService.format_export_data(projects, field_map)
    
    @staticmethod
    def format_client_export_data(clients):
        """Format client data for CSV export using generic formatter"""
        field_map = {
            'name': 'name',
            'entity_type': lambda client: client.entity_type or '',
            'email': lambda client: client.email or '',
            'phone': lambda client: client.phone or '',
            'address': lambda client: client.address or '',
            'contact_person': lambda client: client.contact_person or '',
            'tax_id': lambda client: client.tax_id or '',
            'active_projects': lambda client: Project.query.filter_by(client_id=client.id, status='Active').count(),
            'notes': lambda client: client.notes or '',
            'created_at': lambda client: client.created_at.strftime('%Y-%m-%d %H:%M:%S') if client.created_at else ''
        }
        
        return ExportService.format_export_data(clients, field_map)