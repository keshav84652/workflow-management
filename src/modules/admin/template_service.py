"""
TemplateService: Handles all business logic for templates and related operations.
Updated to use instance methods and extract template management from AdminService.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from src.shared.database.db_import import db
from src.modules.project.models import Template, Task, TemplateTask, Project
from src.models.auth import ActivityLog
from src.modules.project.models import TaskComment
from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.base import BaseService, transactional


class TemplateService(BaseService):
    def __init__(self):
        super().__init__()
    
    def get_templates_by_firm(self, firm_id):
        """Get all templates for a specific firm"""
        return Template.query.filter_by(firm_id=firm_id).order_by(Template.created_at.desc()).all()
    
    def get_template_by_id(self, template_id: int, firm_id: int) -> Optional[Template]:
        """Get template by ID with firm access check"""
        return Template.query.filter_by(id=template_id, firm_id=firm_id).first()
    
    @transactional
    def create_template(self, name: str, description: str, task_dependency_mode: bool,
                       firm_id: int, tasks_data: List[Dict[str, Any]], user_id: int = None) -> Dict[str, Any]:
        """Create a new template with tasks (extracted from AdminService)"""
        try:
            if not name or not name.strip():
                return {
                    'success': False,
                    'message': 'Template name is required'
                }
            
            template = Template(
                name=name.strip(),
                description=description.strip() if description else '',
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
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='TEMPLATE',
                    operation='CREATE',
                    entity_id=template.id,
                    entity_name=template.name,
                    details=f'Template created with {len(tasks_data)} tasks',
                    user_id=user_id
                )
            
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
    def update_template(self, template_id: int, name: str, description: str,
                       task_dependency_mode: bool, firm_id: int,
                       tasks_data: List[Dict[str, Any]], user_id: int = None) -> Dict[str, Any]:
        """Update an existing template (extracted from AdminService)"""
        try:
            template = self.get_template_by_id(template_id, firm_id)
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
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='TEMPLATE',
                    operation='UPDATE',
                    entity_id=template.id,
                    entity_name=template.name,
                    details=f'Template updated with {len(tasks_data)} tasks',
                    user_id=user_id
                )
            
            return {
                'success': True,
                'message': 'Template updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating template: {str(e)}'
            }
    
    @transactional
    def delete_template(self, template_id: int, firm_id: int, user_id: int = None) -> Dict[str, Any]:
        """Delete a template and all its associated tasks (extracted from AdminService)"""
        try:
            template = self.get_template_by_id(template_id, firm_id)
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
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='TEMPLATE',
                    operation='DELETE',
                    entity_id=template_id,
                    entity_name=template_name,
                    details='Template deleted',
                    user_id=user_id
                )
            
            return {
                'success': True,
                'message': f'Template "{template_name}" deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting template: {str(e)}'
            }
