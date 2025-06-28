"""
Admin service layer for business logic
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from flask import session
import os

from core.db_import import db
from models import Firm, User, WorkType, TaskStatus, Template, TemplateTask, Task, Project
from utils.consolidated import generate_access_code
from services.activity_logging_service import ActivityLoggingService as ActivityService
from repositories.firm_repository import FirmRepository
from repositories.user_repository import UserRepository
from repositories.template_repository import TemplateRepository
from repositories.task_repository import TaskRepository
from repositories.project_repository import ProjectRepository
from services.base import BaseService, transactional
from services.worktype_service import WorkTypeService
from services.template_service import TemplateService


class AdminService(BaseService):
    """Service class for administrative business operations"""
    
    def __init__(self):
        super().__init__()
        self.firm_repository = FirmRepository()
        self.user_repository = UserRepository()
        self.template_repository = TemplateRepository()
        self.task_repository = TaskRepository()
        self.project_repository = ProjectRepository()
        self.worktype_service = WorkTypeService()
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
    

    @staticmethod
    def is_admin_authenticated() -> bool:
        """
        Check if current session has admin privileges
        
        Returns:
            True if admin is authenticated, False otherwise
        """
        return session.get('admin', False)
    

    @staticmethod
    def set_admin_session() -> None:
        """Set admin authentication in session"""
        session['admin'] = True
    

    @staticmethod
    def clear_admin_session() -> None:
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
        total_users = User.query.count()
        total_projects = Project.query.count()
        total_tasks = Task.query.count()
        
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
    

    

    

    

    

    

    

    

    

    

    

    

