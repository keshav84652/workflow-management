"""
Admin service layer for business logic
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from flask import session
import os

from core import db
from models import Firm, User, WorkType, TaskStatus, Template, TemplateTask, Task, Project
from utils import generate_access_code, create_activity_log


class AdminService:
    """Service class for administrative business operations"""
    
    @staticmethod
    def authenticate_admin(password: str) -> Dict[str, Any]:
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
    
    @staticmethod
    def get_all_firms() -> List[Firm]:
        """
        Get all firms in the system
        
        Returns:
            List of all Firm objects
        """
        return Firm.query.all()
    
    @staticmethod
    def get_firm_statistics() -> Dict[str, Any]:
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
    
    @staticmethod
    def generate_firm_access_code(firm_name: str) -> Dict[str, Any]:
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
            db.session.commit()
            
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
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error generating access code: {str(e)}',
                'firm': None
            }
    
    @staticmethod
    def toggle_firm_status(firm_id: int) -> Dict[str, Any]:
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
            db.session.commit()
            
            status = 'activated' if firm.is_active else 'deactivated'
            return {
                'success': True,
                'message': f'Firm "{firm.name}" {status} successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating firm status: {str(e)}'
            }
    
    @staticmethod
    def get_templates_for_firm(firm_id: int) -> List[Template]:
        """
        Get all templates for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of Template objects for the firm
        """
        return Template.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def create_template(name: str, description: str, task_dependency_mode: bool,
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
            
            db.session.commit()
            
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
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating template: {str(e)}',
                'template': None
            }
    
    @staticmethod
    def get_template_by_id(template_id: int, firm_id: int) -> Optional[Template]:
        """
        Get a template by ID, ensuring it belongs to the firm
        
        Args:
            template_id: The template's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Template object if found and belongs to firm, None otherwise
        """
        return Template.query.filter_by(id=template_id, firm_id=firm_id).first()
    
    @staticmethod
    def update_template(template_id: int, name: str, description: str,
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
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Template updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating template: {str(e)}'
            }
    
    @staticmethod
    def delete_template(template_id: int, firm_id: int) -> Dict[str, Any]:
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
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Template "{template_name}" deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error deleting template: {str(e)}'
            }
    
    @staticmethod
    def get_work_types_for_firm(firm_id: int) -> List[WorkType]:
        """
        Get all work types for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of WorkType objects for the firm
        """
        return WorkType.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def create_user(name: str, role: str, firm_id: int) -> Dict[str, Any]:
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
            db.session.commit()
            
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
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating user: {str(e)}',
                'user': None
            }