"""
WorkTypeService: Handles all business logic for work type operations.
Updated to use instance methods and extract functionality from AdminService.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from core.db_import import db
from models import WorkType, Template, TaskStatus, Task, Project
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService, transactional


class WorkTypeService(BaseService):
    def __init__(self):
        super().__init__()
    
    def get_work_types_for_firm(self, firm_id, active_only=True):
        """Get all work types for a firm"""
        try:
            query = WorkType.query.filter_by(firm_id=firm_id)
            if active_only:
                query = query.filter_by(is_active=True)
            
            return {
                'success': True,
                'work_types': query.all()
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving work types: {str(e)}'
            }
    
    def get_work_type_by_id(self, work_type_id, firm_id):
        """Get work type by ID with firm access check"""
        try:
            work_type = WorkType.query.filter_by(
                id=work_type_id, 
                firm_id=firm_id
            ).first()
            
            return {
                'success': True,
                'work_type': work_type
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving work type: {str(e)}'
            }
    
    def get_template_for_work_type(self, work_type_id, firm_id):
        """Get template associated with work type"""
        try:
            template = Template.query.filter_by(
                work_type_id=work_type_id,
                firm_id=firm_id
            ).first()
            
            return {
                'success': True,
                'template': template
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving template: {str(e)}'
            }
    
    def get_task_statuses_for_work_type(self, work_type_id):
        """Get task statuses (kanban columns) for work type"""
        try:
            statuses = TaskStatus.query.filter_by(
                work_type_id=work_type_id
            ).order_by(TaskStatus.position.asc()).all()
            
            return {
                'success': True,
                'statuses': statuses
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving task statuses: {str(e)}'
            }
    
    def get_work_type_usage_stats(self, firm_id: int) -> Dict[int, int]:
        """Get usage statistics for work types (number of tasks using each work type)"""
        try:
            work_types_result = self.get_work_types_for_firm(firm_id)
            if not work_types_result['success']:
                return {}
            
            work_types = work_types_result['work_types']
            usage_stats = {}
            
            for wt in work_types:
                task_count = Task.query.join(Project).filter(
                    Task.firm_id == firm_id,
                    Project.work_type_id == wt.id
                ).count()
                usage_stats[wt.id] = task_count
            
            return usage_stats
        except Exception as e:
            return {}
    
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
    
    @transactional
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
    
    @transactional
    def create_work_type(self, name: str, description: str, firm_id: int, user_id: int = None) -> Dict[str, Any]:
        """Create a new work type with default statuses"""
        try:
            if not name or not name.strip():
                return {
                    'success': False,
                    'message': 'Work type name is required'
                }
            
            work_type = WorkType(
                name=name.strip(),
                description=description.strip() if description else '',
                firm_id=firm_id,
                is_active=True
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
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='WORK_TYPE',
                    operation='CREATE',
                    entity_id=work_type.id,
                    entity_name=work_type.name,
                    details=f'Work type created with {len(default_statuses)} default statuses',
                    user_id=user_id
                )
            
            return {
                'success': True,
                'message': f'Work type "{name}" created successfully with default statuses',
                'work_type': {
                    'id': work_type.id,
                    'name': work_type.name,
                    'description': work_type.description
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating work type: {str(e)}',
                'work_type': None
            }
    
    @transactional
    def update_work_type(self, work_type_id: int, name: str, description: str, 
                        firm_id: int, user_id: int = None) -> Dict[str, Any]:
        """Update an existing work type"""
        try:
            work_type_result = self.get_work_type_by_id(work_type_id, firm_id)
            if not work_type_result['success'] or not work_type_result['work_type']:
                return {
                    'success': False,
                    'message': 'Work type not found or access denied'
                }
            
            work_type = work_type_result['work_type']
            
            if not name or not name.strip():
                return {
                    'success': False,
                    'message': 'Work type name is required'
                }
            
            old_name = work_type.name
            work_type.name = name.strip()
            work_type.description = description.strip() if description else ''
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='WORK_TYPE',
                    operation='UPDATE',
                    entity_id=work_type.id,
                    entity_name=work_type.name,
                    details=f'Work type updated from "{old_name}" to "{work_type.name}"',
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
