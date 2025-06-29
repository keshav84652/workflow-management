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
        
        # Get total projects and tasks using direct database queries to avoid circular dependencies
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
    
    def get_work_types_for_firm(self, firm_id: int) -> Dict[str, Any]:
        """
        Get all work types for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict containing success status and work types list
        """
        try:
            work_types = WorkType.query.filter_by(firm_id=firm_id).order_by(WorkType.name.asc()).all()
            work_types_data = []
            
            for wt in work_types:
                # Get associated task statuses
                statuses = TaskStatus.query.filter_by(work_type_id=wt.id).order_by(TaskStatus.position.asc()).all()
                statuses_data = [{
                    'id': status.id,
                    'name': status.name,
                    'color': status.color,
                    'position': status.position,
                    'is_default': status.is_default,
                    'is_terminal': status.is_terminal
                } for status in statuses]
                
                work_types_data.append({
                    'id': wt.id,
                    'name': wt.name,
                    'description': wt.description,
                    'statuses': statuses_data
                })
            
            return {
                'success': True,
                'work_types': work_types_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving work types: {str(e)}',
                'work_types': []
            }
    
    def get_work_type_usage_stats(self, firm_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for work types
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict containing usage statistics
        """
        try:
            # Get count of projects using each work type
            usage_stats = db.session.query(
                WorkType.id,
                WorkType.name,
                func.count(Project.id).label('project_count')
            ).outerjoin(Project, WorkType.id == Project.work_type_id)\
             .filter(WorkType.firm_id == firm_id)\
             .group_by(WorkType.id, WorkType.name)\
             .all()
            
            return {wt_id: {'name': name, 'project_count': count} 
                    for wt_id, name, count in usage_stats}
            
        except Exception as e:
            return {}
    
    @transactional
    def create_work_type(self, name: str, description: str, firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a new work type
        
        Args:
            name: Work type name
            description: Work type description
            firm_id: The firm's ID
            user_id: ID of user creating the work type
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            if not name or not name.strip():
                return {'success': False, 'message': 'Work type name is required'}
            
            # Check if work type already exists for this firm
            existing = WorkType.query.filter_by(name=name.strip(), firm_id=firm_id).first()
            if existing:
                return {'success': False, 'message': 'Work type with this name already exists'}
            
            work_type = WorkType(
                name=name.strip(),
                description=description.strip() if description else '',
                firm_id=firm_id
            )
            
            db.session.add(work_type)
            db.session.flush()  # Get the ID
            
            # Create default task statuses
            default_statuses = [
                {'name': 'Not Started', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'In Progress', 'color': '#3b82f6', 'position': 2},
                {'name': 'Review', 'color': '#f59e0b', 'position': 3},
                {'name': 'Completed', 'color': '#10b981', 'position': 4, 'is_terminal': True}
            ]
            
            for status_data in default_statuses:
                status = TaskStatus(
                    name=status_data['name'],
                    color=status_data['color'],
                    position=status_data['position'],
                    is_default=status_data.get('is_default', False),
                    is_terminal=status_data.get('is_terminal', False),
                    work_type_id=work_type.id
                )
                db.session.add(status)
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='WORK_TYPE',
                operation='CREATE',
                entity_id=work_type.id,
                entity_name=work_type.name,
                details=f'Work type created with description: {description}',
                user_id=user_id
            )
            
            return {
                'success': True,
                'message': f'Work type "{name}" created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating work type: {str(e)}'
            }
    
    @transactional
    def update_work_type(self, work_type_id: int, name: str, description: str, firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update an existing work type
        
        Args:
            work_type_id: ID of work type to update
            name: New work type name
            description: New work type description
            firm_id: The firm's ID (for security)
            user_id: ID of user updating the work type
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
            if not work_type:
                return {'success': False, 'message': 'Work type not found or access denied'}
            
            if not name or not name.strip():
                return {'success': False, 'message': 'Work type name is required'}
            
            # Check if another work type with this name exists
            existing = WorkType.query.filter(
                WorkType.name == name.strip(),
                WorkType.firm_id == firm_id,
                WorkType.id != work_type_id
            ).first()
            if existing:
                return {'success': False, 'message': 'Work type with this name already exists'}
            
            old_name = work_type.name
            work_type.name = name.strip()
            work_type.description = description.strip() if description else ''
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='WORK_TYPE',
                operation='UPDATE',
                entity_id=work_type.id,
                entity_name=work_type.name,
                details=f'Work type updated from "{old_name}" to "{name}"',
                user_id=user_id
            )
            
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
            work_type_id: ID of the work type
            name: Status name
            color: Status color (hex)
            firm_id: The firm's ID (for security)
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            # Verify work type belongs to firm
            work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
            if not work_type:
                return {'success': False, 'message': 'Work type not found or access denied'}
            
            if not name or not name.strip():
                return {'success': False, 'message': 'Status name is required'}
            
            # Check if status already exists for this work type
            existing = TaskStatus.query.filter_by(name=name.strip(), work_type_id=work_type_id).first()
            if existing:
                return {'success': False, 'message': 'Status with this name already exists for this work type'}
            
            # Get next position
            max_position = db.session.query(func.max(TaskStatus.position)).filter_by(work_type_id=work_type_id).scalar() or 0
            
            status = TaskStatus(
                name=name.strip(),
                color=color or '#6b7280',
                position=max_position + 1,
                work_type_id=work_type_id
            )
            
            db.session.add(status)
            
            return {
                'success': True,
                'message': f'Status "{name}" created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating status: {str(e)}'
            }
    
    @transactional
    def update_task_status(self, status_id: int, name: str, color: str, position: int, 
                          is_default: bool, is_terminal: bool, firm_id: int) -> Dict[str, Any]:
        """
        Update an existing task status
        
        Args:
            status_id: ID of status to update
            name: New status name
            color: New status color
            position: New position
            is_default: Whether this is the default status
            is_terminal: Whether this is a terminal status
            firm_id: The firm's ID (for security)
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            # Get status and verify it belongs to firm
            status = db.session.query(TaskStatus).join(WorkType).filter(
                TaskStatus.id == status_id,
                WorkType.firm_id == firm_id
            ).first()
            
            if not status:
                return {'success': False, 'message': 'Status not found or access denied'}
            
            if not name or not name.strip():
                return {'success': False, 'message': 'Status name is required'}
            
            # If setting as default, remove default from other statuses in same work type
            if is_default:
                TaskStatus.query.filter_by(work_type_id=status.work_type_id).update({'is_default': False})
            
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
    

    

    

    

    

    

    

    

    

    

    

    

