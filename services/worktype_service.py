"""
WorkTypeService: Handles all business logic for work type operations.
"""

from core.db_import import db
from models import WorkType, Template, TaskStatus


class WorkTypeService:
    @staticmethod
    def get_work_types_for_firm(firm_id, active_only=True):
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
    
    @staticmethod
    def get_work_type_by_id(work_type_id, firm_id):
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
    
    @staticmethod
    def get_template_for_work_type(work_type_id, firm_id):
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
    
    @staticmethod
    def get_task_statuses_for_work_type(work_type_id):
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