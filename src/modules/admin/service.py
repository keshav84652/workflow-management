"""
Admin service layer for business logic
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from flask import session
import os

from src.shared.database.db_import import db
from src.models import Firm, User, WorkType, TaskStatus, Template, TemplateTask, Task, Project
from src.shared.utils.consolidated import generate_access_code
from src.shared.services import ActivityLoggingService as ActivityService
from src.modules.auth.firm_repository import FirmRepository
from src.modules.auth.repository import UserRepository
from src.modules.admin.template_repository import TemplateRepository
from src.shared.base import BaseService, transactional
from src.modules.admin.template_service import TemplateService
from sqlalchemy import func


class AdminService(BaseService):
    """Service class for administrative business operations"""
    
    def __init__(self):
        super().__init__()
        self.firm_repository = FirmRepository()
        self.user_repository = UserRepository()
        self.template_repository = TemplateRepository()
        self.template_service = TemplateService()
    
    def authenticate_admin(self, password: str) -> Dict[str, Any]:
        """
        Authenticate admin user with password
        
        Args:
            password: Admin password to verify
            
        Returns:
            Dict containing success status and any error messages
        """
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if password == admin_password:
            return {
                'success': True,
                'message': 'Admin authentication successful'
            }
        else:
            return {
                'success': False,
                'message': 'Invalid admin password'
            }
    

    def is_admin_authenticated(self) -> bool:
        """
        Check if current session has admin privileges
        
        Returns:
            True if admin is authenticated, False otherwise
        """
        return session.get('admin', False)
    

    def set_admin_session(self) -> None:
        """Set admin authentication in session"""
        session['admin'] = True
    

    def clear_admin_session(self) -> None:
        """Clear admin authentication from session"""
        session.pop('admin', None)
    

    def get_all_firms(self) -> List[Firm]:
        """
        Get all firms in the system
        
        Returns:
            List of all Firm objects
        """
        return self.firm_repository.get_all()
    

    def get_firm_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide statistics
        
        Returns:
            Dictionary containing various system statistics
        """
        firms = self.firm_repository.get_all()
        total_firms = len(firms)
        active_firms = len([f for f in firms if f.is_active])
        
        # Get total users across all firms
        total_users = 0
        for firm in firms:
            total_users += len(self.user_repository.get_by_firm(firm.id))
        
        # Use service layer for cross-module data
        from src.modules.project.service import ProjectService
        from src.modules.project.task_service import TaskService
        
        project_service = ProjectService()
        task_service = TaskService()
        
        # Get total projects and tasks across all firms
        total_projects = 0
        total_tasks = 0
        for firm in firms:
            projects = project_service.get_projects_by_firm(firm.id)
            total_projects += len(projects)
            
            tasks_result = task_service.get_tasks_by_firm(firm.id)
            if tasks_result['success']:
                total_tasks += len(tasks_result['tasks'])
        
        return {
            'total_firms': total_firms,
            'active_firms': active_firms,
            'inactive_firms': total_firms - active_firms,
            'total_users': total_users,
            'total_projects': total_projects,
            'total_tasks': total_tasks
        }
    

    @transactional
    def generate_firm_access_code(self, firm_name: str) -> Dict[str, Any]:
        """
        Generate a new access code for a firm
        
        Args:
            firm_name: Name of the firm
            
        Returns:
            Dict containing success status, firm data, and any error messages
        """
        try:
            # Generate unique access code
            access_code = generate_access_code()
            
            # Ensure code is unique
            while self.firm_repository.get_by_access_code(access_code, active_only=False):
                access_code = generate_access_code()
            
            # Create new firm
            firm = Firm(
                name=firm_name.strip(),
                access_code=access_code,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(firm)
            
            return {
                'success': True,
                'message': f'Access code generated successfully for {firm_name}',
                'firm': {
                    'id': firm.id,
                    'name': firm.name,
                    'access_code': firm.access_code
                }
            }
            
        except Exception as e:
            # @transactional decorator handles rollback automatically
            return {
                'success': False,
                'message': f'Error generating access code: {str(e)}',
                'firm': None
            }
    

    @transactional
    def toggle_firm_status(self, firm_id: int) -> Dict[str, Any]:
        """
        Toggle a firm's active status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            firm = self.firm_repository.get_by_id(firm_id)
            if not firm:
                return {
                    'success': False,
                    'message': 'Firm not found'
                }
            
            firm.is_active = not firm.is_active
            
            status = 'activated' if firm.is_active else 'deactivated'
            return {
                'success': True,
                'message': f'Firm "{firm.name}" {status} successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating firm status: {str(e)}'
            }
    

    

    

    

    

    

    

    

    

    

    

    

