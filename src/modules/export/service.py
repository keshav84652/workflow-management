"""
Export Service for CPA WorkflowPilot
Handles data export logic for various formats and entities.
"""

import csv
import io
from typing import Dict, Any, List
from datetime import datetime
from flask import make_response, jsonify

from src.shared.base import BaseService


class ExportService(BaseService):
    """Service for handling data exports"""
    
    def __init__(self):
        super().__init__()
    
    def export_projects_csv(self, firm_id: int) -> Any:
        """Export projects as CSV"""
        try:
            from src.modules.project.service import ProjectService
            
            project_service = ProjectService()
            result = project_service.get_projects_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            projects = result['projects']
            
            # Create CSV content
            csv_content = self._create_projects_csv(projects)
            
            # Create response
            response = make_response(csv_content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=projects_export_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_projects_json(self, firm_id: int) -> Any:
        """Export projects as JSON"""
        try:
            from src.modules.project.service import ProjectService
            
            project_service = ProjectService()
            result = project_service.get_projects_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            response_data = {
                'export_date': datetime.now().isoformat(),
                'firm_id': firm_id,
                'projects': result['projects']
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Disposition'] = f'attachment; filename=projects_export_{datetime.now().strftime("%Y%m%d")}.json'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_clients_csv(self, firm_id: int) -> Any:
        """Export clients as CSV"""
        try:
            from src.modules.client.service import ClientService
            
            client_service = ClientService()
            result = client_service.get_clients_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            clients = result['clients']
            
            # Create CSV content
            csv_content = self._create_clients_csv(clients)
            
            # Create response
            response = make_response(csv_content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_clients_json(self, firm_id: int) -> Any:
        """Export clients as JSON"""
        try:
            from src.modules.client.service import ClientService
            
            client_service = ClientService()
            result = client_service.get_clients_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            response_data = {
                'export_date': datetime.now().isoformat(),
                'firm_id': firm_id,
                'clients': result['clients']
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d")}.json'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_tasks_csv(self, firm_id: int) -> Any:
        """Export tasks as CSV"""
        try:
            from src.modules.project.task_service import TaskService
            
            task_service = TaskService()
            result = task_service.get_tasks_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            tasks = result['tasks']
            
            # Create CSV content
            csv_content = self._create_tasks_csv(tasks)
            
            # Create response
            response = make_response(csv_content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_tasks_json(self, firm_id: int) -> Any:
        """Export tasks as JSON"""
        try:
            from src.modules.project.task_service import TaskService
            
            task_service = TaskService()
            result = task_service.get_tasks_by_firm(firm_id)
            
            if not result['success']:
                return {'success': False, 'error': result['message']}
            
            response_data = {
                'export_date': datetime.now().isoformat(),
                'firm_id': firm_id,
                'tasks': result['tasks']
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Content-Disposition'] = f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.json'
            
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_projects_csv(self, projects: List[Dict[str, Any]]) -> str:
        """Create CSV content for projects"""
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
        
        return output.getvalue()
    
    def _create_clients_csv(self, clients: List[Dict[str, Any]]) -> str:
        """Create CSV content for clients"""
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
        
        return output.getvalue()
    
    def _create_tasks_csv(self, tasks: List[Dict[str, Any]]) -> str:
        """Create CSV content for tasks"""
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
        
        return output.getvalue()