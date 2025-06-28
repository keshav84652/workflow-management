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


class AdminService(BaseService):
    """Service class for administrative business operations"""
    
    def __init__(self):
        super().__init__()
        self.firm_repository = FirmRepository()
        self.user_repository = UserRepository()
        self.template_repository = TemplateRepository()
        self.task_repository = TaskRepository()
        self.project_repository = ProjectRepository()
    
    def authenticate_admin(self, self, password: str) -> Dict[str, Any]:
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
    

    def get_all_firms(self, self) -> List[Firm]:
        """
        Get all firms in the system
        
        Returns:
            List of all Firm objects
        """
        return Firm.query.order_by(Firm.created_at.desc()).all()
    

    def get_firm_statistics(self, self) -> Dict[str, Any]:
        """
        Get system-wide statistics
        
        Returns:
            Dictionary containing various system statistics
        """
        total_firms = Firm.query.count()
        active_firms = Firm.query.filter_by(is_active=True).count()
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
    def generate_firm_access_code(self, self, firm_name: str) -> Dict[str, Any]:
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
            while Firm.query.filter_by(access_code=access_code).first():
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
    def toggle_firm_status(self, self, firm_id: int) -> Dict[str, Any]:
        """
        Toggle a firm's active status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            firm = Firm.query.get(firm_id)
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
    

    @transactional
    def get_templates_for_firm(self, firm_id: int) -> List[Template]:
        """
        Get all templates for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of Template objects for the firm
        """
        return Template.query.filter_by(firm_id=firm_id).order_by(Template.created_at.desc()).all()
    

    @transactional
    def create_template(self, name: str, description: str, task_dependency_mode: bool,
                       firm_id: int, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new template with tasks
        
        Args:
            name: Template name
            description: Template description
            task_dependency_mode: Whether tasks should be sequential
            firm_id: The firm's ID
            tasks_data: List of dictionaries containing task information
            
        Returns:
            Dict containing success status, template data, and any error messages
        """
        try:
            template = Template(
                name=name.strip(),
                description=description.strip(),
                task_dependency_mode=task_dependency_mode,
                firm_id=firm_id
            )
            
            db.session.add(template)
            db.session.flush()  # Get template ID
            
            # Add template tasks
            for i, task_data in enumerate(tasks_data):
                if task_data.get('title', '').strip():
                    template_task = TemplateTask(
                        title=task_data['title'].strip(),
                        description=task_data.get('description', '').strip(),
                        recurrence_rule=task_data.get('recurrence_rule'),
                        order=i,
                        template_id=template.id
                    )
                    db.session.add(template_task)
            
            
            # Auto-create work type from template
            work_type_created = False
            try:
                template.create_work_type_from_template()
                work_type_created = True
            except Exception as e:
                print(f"Work type creation failed: {e}")
            
            return {
                'success': True,
                'message': 'Template created successfully' + 
                          (' with workflow' if work_type_created else ''),
                'template': {
                    'id': template.id,
                    'name': template.name
                },
                'work_type_created': work_type_created
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating template: {str(e)}',
                'template': None
            }
    

    @transactional
    def get_template_by_id(self, template_id: int, firm_id: int) -> Optional[Template]:
        """
        Get a template by ID, ensuring it belongs to the firm
        
        Args:
            template_id: The template's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Template object if found and belongs to firm, None otherwise
        """
        return Template.query.filter_by(id=template_id, firm_id=firm_id).first()
    

    @transactional
    def update_template(self, template_id: int, name: str, description: str,
                       task_dependency_mode: bool, firm_id: int,
                       tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update an existing template
        
        Args:
            template_id: The template's ID
            name: Updated template name
            description: Updated template description
            task_dependency_mode: Whether tasks should be sequential
            firm_id: The firm's ID for security check
            tasks_data: List of dictionaries containing updated task information
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            template = AdminService.get_template_by_id(template_id, firm_id)
            if not template:
                return {
                    'success': False,
                    'message': 'Template not found or access denied'
                }
            
            # Update template basic info
            template.name = name.strip()
            template.description = description.strip()
            template.task_dependency_mode = task_dependency_mode
            
            # Remove existing template tasks
            TemplateTask.query.filter_by(template_id=template_id).delete()
            
            # Add updated template tasks
            for i, task_data in enumerate(tasks_data):
                if task_data.get('title', '').strip():
                    template_task = TemplateTask(
                        title=task_data['title'].strip(),
                        description=task_data.get('description', '').strip(),
                        recurrence_rule=task_data.get('recurrence_rule'),
                        order=i,
                        template_id=template.id
                    )
                    db.session.add(template_task)
            
            
            return {
                'success': True,
                'message': 'Template updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating template: {str(e)}'
            }
    

    def delete_template(self, self, template_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Delete a template and all its associated tasks
        
        Args:
            template_id: The template's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            template = AdminService.get_template_by_id(template_id, firm_id)
            if not template:
                return {
                    'success': False,
                    'message': 'Template not found or access denied'
                }
            
            template_name = template.name
            
            # Check if template is being used by any projects
            projects_using_template = Project.query.filter_by(template_id=template_id).count()
            if projects_using_template > 0:
                return {
                    'success': False,
                    'message': f'Cannot delete template "{template_name}" - it is being used by {projects_using_template} project(s)'
                }
            
            # Delete template (cascade will handle template tasks)
            db.session.delete(template)
            
            return {
                'success': True,
                'message': f'Template "{template_name}" deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting template: {str(e)}'
            }
    

    @transactional
    def get_work_types_for_firm(self, firm_id: int) -> List[WorkType]:
        """
        Get all work types for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of WorkType objects for the firm
        """
        return WorkType.query.filter_by(firm_id=firm_id).all()
    

    @transactional
    def get_work_type_usage_stats(self, firm_id: int) -> Dict[int, int]:
        """
        Get usage statistics for work types (number of tasks using each work type)
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict mapping work_type_id to task count
        """
        work_types = AdminService.get_work_types_for_firm(firm_id)
        usage_stats = {}
        
        for wt in work_types:
            task_count = Task.query.join(Project).filter(
                Task.firm_id == firm_id,
                Project.work_type_id == wt.id
            ).count()
            usage_stats[wt.id] = task_count
        
        return usage_stats
    

    @transactional
    def create_work_type(self, name: str, description: str, firm_id: int) -> Dict[str, Any]:
        """
        Create a new work type with default statuses
        
        Args:
            name: Work type name
            description: Work type description
            firm_id: The firm's ID
            
        Returns:
            Dict containing success status, work type data, and any error messages
        """
        try:
            work_type = WorkType(
                name=name.strip(),
                description=description.strip(),
                firm_id=firm_id
            )
            db.session.add(work_type)
            db.session.flush()  # Get work_type ID
            
            # Create default statuses
            default_statuses = [
                {'name': 'Not Started', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'In Progress', 'color': '#3b82f6', 'position': 2},
                {'name': 'Review', 'color': '#f59e0b', 'position': 3},
                {'name': 'Completed', 'color': '#10b981', 'position': 4, 'is_terminal': True}
            ]
            
            for status_data in default_statuses:
                status = TaskStatus(
                    firm_id=firm_id,
                    work_type_id=work_type.id,
                    **status_data
                )
                db.session.add(status)
            
            
            return {
                'success': True,
                'message': f'Work type "{name}" created successfully with default statuses',
                'work_type': {
                    'id': work_type.id,
                    'name': work_type.name
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating work type: {str(e)}',
                'work_type': None
            }
    

    @transactional
    def update_work_type(self, work_type_id: int, name: str, description: str, firm_id: int) -> Dict[str, Any]:
        """
        Update an existing work type
        
        Args:
            work_type_id: The work type's ID
            name: Updated work type name
            description: Updated work type description
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
            if not work_type:
                return {
                    'success': False,
                    'message': 'Work type not found or access denied'
                }
            
            work_type.name = name.strip()
            work_type.description = description.strip()
            
            return {
                'success': True,
                'message': f'Work type "{name}" updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating work type: {str(e)}'
            }
    

    @transactional
    def create_task_status(self, work_type_id: int, name: str, color: str, firm_id: int) -> Dict[str, Any]:
        """
        Create a new task status for a work type
        
        Args:
            work_type_id: The work type's ID
            name: Status name
            color: Status color (hex)
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status, status data, and any error messages
        """
        try:
            # Verify work type belongs to firm
            work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
            if not work_type:
                return {
                    'success': False,
                    'message': 'Work type not found or access denied'
                }
            
            # Get next position
            max_position = db.session.query(db.func.max(TaskStatus.position)).filter_by(
                work_type_id=work_type_id
            ).scalar() or 0
            
            status = TaskStatus(
                firm_id=firm_id,
                work_type_id=work_type_id,
                name=name.strip(),
                color=color,
                position=max_position + 1
            )
            
            db.session.add(status)
            
            return {
                'success': True,
                'message': f'Status "{name}" created successfully',
                'status': {
                    'id': status.id,
                    'name': status.name,
                    'color': status.color
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating status: {str(e)}',
                'status': None
            }
    

    def update_task_status(self, status_id: int, name: str, color: str, position: int,
                          is_default: bool, is_terminal: bool, firm_id: int) -> Dict[str, Any]:
        """
        Update an existing task status
        
        Args:
            status_id: The status's ID
            name: Updated status name
            color: Updated status color
            position: Updated status position
            is_default: Whether this is the default status
            is_terminal: Whether this is a terminal status
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            status = TaskStatus.query.filter_by(id=status_id, firm_id=firm_id).first()
            if not status:
                return {
                    'success': False,
                    'message': 'Status not found or access denied'
                }
            
            status.name = name.strip()
            status.color = color
            status.position = position
            status.is_default = is_default
            status.is_terminal = is_terminal
            
            
            return {
                'success': True,
                'message': f'Status "{name}" updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating status: {str(e)}'
            }
    

    def create_user(self, self, name: str, role: str, firm_id: int) -> Dict[str, Any]:
        """
        Create a new user for a firm
        
        Args:
            name: User's name
            role: User's role (Admin, Member, etc.)
            firm_id: The firm's ID
            
        Returns:
            Dict containing success status, user data, and any error messages
        """
        try:
            # Validate role
            valid_roles = ['Admin', 'Member', 'Staff', 'Senior', 'Manager', 'Partner']
            if role not in valid_roles:
                return {
                    'success': False,
                    'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
                }
            
            user = User(
                name=name.strip(),
                role=role,
                firm_id=firm_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(user)
            
            return {
                'success': True,
                'message': f'User "{name}" created successfully',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'role': user.role
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating user: {str(e)}',
                'user': None
            }