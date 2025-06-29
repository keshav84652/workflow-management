"""
ProjectService: Handles all business logic for project operations.
"""

from core.db_import import db
from src.models import Project, Task, Client, User, WorkType
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService, transactional
from repositories.project_repository import ProjectRepository


class ProjectService(BaseService):
    def __init__(self):
        super().__init__()
        self.project_repository = ProjectRepository()
    def get_projects_for_firm(self, firm_id, include_inactive=False):
        """Get all projects for a firm"""
        return self.project_repository.get_by_firm(firm_id, include_inactive)
    
    def get_project_by_id_and_firm(self, project_id, firm_id):
        """Get project by ID with firm access check"""
        return self.project_repository.get_by_id_and_firm(project_id, firm_id)
    
    def get_project_progress(self, project_id, firm_id):
        """Get project progress with access check"""
        project = self.get_project_by_id_and_firm(project_id, firm_id)
        if not project:
            return {'error': 'Project not found or access denied'}, 403
        
        from repositories.task_repository import TaskRepository
        task_repo = TaskRepository()
        project_tasks = task_repo.get_project_tasks(project_id, firm_id, include_completed=True)
        total_tasks = len(project_tasks)
        completed_tasks = len([t for t in project_tasks if t.status == 'Completed'])
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'project_id': project.id,
            'project_name': project.name,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress_percentage': round(progress_percentage, 1)
        }
    
    @transactional
    def create_project(self, name, description=None, client_id=None, work_type_id=None, firm_id=None, user_id=None):
        """Create a new project"""
        try:
            if not name or not name.strip():
                return {'success': False, 'message': 'Project name is required'}
            
            # Verify client belongs to firm
            if client_id:
                client = Client.query.filter_by(id=client_id, firm_id=firm_id).first()
                if not client:
                    return {'success': False, 'message': 'Client not found or access denied'}
            
            # Verify work type belongs to firm
            if work_type_id:
                work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
                if not work_type:
                    return {'success': False, 'message': 'Work type not found or access denied'}
            
            project = Project(
                name=name.strip(),
                client_id=client_id,
                work_type_id=work_type_id,
                firm_id=firm_id,
                status='Active'
            )
            
            # Set initial workflow status if work type exists
            if work_type_id:
                # Find the default status for this work type
                from src.models import TaskStatus
                default_status = TaskStatus.query.filter_by(
                    work_type_id=work_type_id,
                    is_default=True
                ).first()
                if default_status:
                    project.current_status_id = default_status.id
                else:
                    # Fallback to first status if no default
                    first_status = TaskStatus.query.filter_by(
                        work_type_id=work_type_id
                    ).order_by(TaskStatus.position.asc()).first()
                    if first_status:
                        project.current_status_id = first_status.id
            
            db.session.add(project)
            db.session.commit()
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='PROJECT',
                operation='CREATE',
                entity_id=project.id,
                entity_name=project.name,
                details=f'Project created for client: {client.name if client_id else "No client"}',
                user_id=user_id
            )
            
            # Publish project creation event
            from src.shared.events.schemas import ProjectCreatedEvent
            from src.shared.events.publisher import publish_event
            event = ProjectCreatedEvent(
                project_id=project.id,
                firm_id=firm_id,
                name=project.name,
                client_id=client_id,
                status=project.status
            )
            publish_event(event)
            
            return {
                'success': True,
                'message': 'Project created successfully',
                'project_id': project.id,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'client_id': project.client_id,
                    'work_type_id': project.work_type_id
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @transactional
    def create_project_from_template(self, template_id, client_name, project_name, start_date, due_date=None, priority='Medium', task_dependency_mode=False, firm_id=None, user_id=None):
        """Create a project from a template"""
        try:
            # For now, this can just call the regular create_project method
            # In the future, this could be enhanced to use template-specific logic
            return self.create_project(
                name=project_name,
                description=f"Project created from template with client: {client_name}",
                client_id=None,  # Would need client lookup logic
                work_type_id=None,  # Would need template work type lookup
                firm_id=firm_id,
                user_id=user_id
            )
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @transactional
    def update_project(self, project_id, firm_id, **update_data):
        """Update a project with new data"""
        try:
            project = self.get_project_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            # Update allowed fields
            if 'name' in update_data:
                project.name = update_data['name']
            if 'description' in update_data:
                project.description = update_data['description']
            if 'client_id' in update_data:
                project.client_id = update_data['client_id']
            if 'work_type_id' in update_data:
                project.work_type_id = update_data['work_type_id']
            if 'status' in update_data:
                project.status = update_data['status']
            
            return {'success': True, 'message': 'Project updated successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @transactional
    def delete_project(self, project_id, firm_id):
        """Delete a project"""
        try:
            project = self.get_project_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            # Check if project has tasks  
            from repositories.task_repository import TaskRepository
            task_repo = TaskRepository()
            project_tasks = task_repo.get_project_tasks(project_id, firm_id, include_completed=True)
            task_count = len(project_tasks)
            if task_count > 0:
                return {'success': False, 'message': f'Cannot delete project with {task_count} tasks. Please remove tasks first.'}
            
            db.session.delete(project)
            
            return {'success': True, 'message': 'Project deleted successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @transactional
    def update_project_status(self, project_id, new_status, firm_id, user_id):
        """Update project status"""
        try:
            project = self.get_project_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            old_status = project.status
            project.status = new_status
            
            db.session.commit()
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='PROJECT',
                operation='UPDATE',
                entity_id=project.id,
                entity_name=project.name,
                details=f'Status changed from "{old_status}" to "{new_status}"',
                user_id=user_id
            )
            
            # Publish project updated event
            from src.shared.events.schemas import ProjectUpdatedEvent
            from src.shared.events.publisher import publish_event
            event = ProjectUpdatedEvent(
                project_id=project.id,
                firm_id=firm_id,
                name=project.name,
                changes={'status': {'old': old_status, 'new': new_status}},
                client_id=project.client_id
            )
            publish_event(event)
            
            return {
                'success': True,
                'message': f'Project status updated to {new_status}'
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    def get_active_projects(self, firm_id):
        """Get active projects for a firm"""
        return self.project_repository.get_by_firm(firm_id, include_inactive=False)
    
    def get_project_by_id(self, project_id, firm_id):
        """Get project by ID for firm"""
        return self.get_project_by_id_and_firm(project_id, firm_id)
    
    def get_projects_by_firm(self, firm_id):
        """Get all projects for firm (alias for consistency)"""
        return self.project_repository.get_by_firm(firm_id)
    
    @transactional
    def move_project_status(self, project_id, status_id, firm_id, user_id=None):
        """Move project to different status for Kanban board"""
        try:
            project = self.get_project_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            old_status = project.current_workflow_status_name
            
            # Handle special completed column
            if status_id == 'completed':
                project.status = 'Completed'
                # Mark all project tasks as completed
                for task in project.tasks:
                    if task.status != 'Completed':
                        task.status = 'Completed'
                
                # Find terminal status for this work type
                if project.work_type_id:
                    from src.models import TaskStatus
                    terminal_status = TaskStatus.query.filter_by(
                        work_type_id=project.work_type_id,
                        is_terminal=True
                    ).first()
                    if terminal_status:
                        project.current_status_id = terminal_status.id
                message = 'Project completed'
            else:
                # status_id should be a TaskStatus ID
                try:
                    status_id = int(status_id)
                    from src.models import TaskStatus
                    task_status = TaskStatus.query.filter_by(
                        id=status_id,
                        work_type_id=project.work_type_id
                    ).first()
                    
                    if not task_status:
                        return {'success': False, 'message': 'Invalid status for this project type'}
                    
                    old_status_id = project.current_status_id
                    project.current_status_id = status_id
                    project.status = 'Active'  # Keep as active unless completed
                    
                    # Update project tasks to reflect workflow progression
                    self._update_project_tasks_for_workflow_change(
                        project, old_status_id, status_id
                    )
                    
                    message = f'Project moved to {task_status.name}'
                    
                except (ValueError, TypeError):
                    return {'success': False, 'message': 'Invalid status ID format'}
            
            db.session.commit()
            
            # Log activity if user_id provided
            if user_id:
                ActivityService.log_entity_operation(
                    entity_type='PROJECT',
                    operation='STATUS_MOVE',
                    entity_id=project.id,
                    entity_name=project.name,
                    details=f'Moved from "{old_status}" to "{project.current_workflow_status_name}" via Kanban',
                    user_id=user_id
                )
            
            # Calculate updated progress for response  
            from repositories.task_repository import TaskRepository
            task_repo = TaskRepository()
            project_tasks = task_repo.get_project_tasks(project_id, firm_id, include_completed=True)
            total_tasks = len(project_tasks)
            completed_tasks = len([t for t in project_tasks if t.status == 'Completed'])
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                'success': True,
                'message': message,
                'project_progress': round(progress_percentage, 1),
                'completed_tasks': completed_tasks,
                'total_tasks': total_tasks
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    def _update_project_tasks_for_workflow_change(self, project, old_status_id, new_status_id):
        """
        Update project tasks to reflect workflow progression when project status changes via kanban
        This ensures progress_percentage stays in sync with workflow status
        
        Logic:
        - Column 1: Task 1 = "In Progress", rest = "Not Started" (0% complete)
        - Column 2: Task 1 = "Completed", Task 2 = "In Progress", rest = "Not Started" (20% if 5 tasks)
        - etc.
        """
        try:
            from src.models import TaskStatus
            
            # Get the workflow statuses for this work type in order
            if not project.work_type_id:
                return  # No workflow to update
            
            workflow_statuses = TaskStatus.query.filter_by(
                work_type_id=project.work_type_id
            ).order_by(TaskStatus.position.asc()).all()
            
            if not workflow_statuses:
                return
            
            # Find the position of the new status (0-based index)
            new_position = None
            for i, status in enumerate(workflow_statuses):
                if status.id == new_status_id:
                    new_position = i
                    break
            
            if new_position is None:
                return  # Invalid status ID
            
            # Get all tasks in the project, ordered by creation or workflow order
            project_tasks = list(project.tasks)
            if not project_tasks:
                return  # No tasks to update
                
            # Sort tasks to match workflow order (by id, created_at, or title)
            project_tasks.sort(key=lambda t: t.id)
            
            # Update task statuses based on workflow position
            for i, task in enumerate(project_tasks):
                if i < new_position:
                    # Tasks before current position should be "Completed"
                    task.status = 'Completed'
                elif i == new_position:
                    # Current position task should be "In Progress"
                    task.status = 'In Progress'
                else:
                    # Tasks after current position should be "Not Started"
                    task.status = 'Not Started'
                        
        except Exception as e:
            # Don't fail the main operation if task updates fail
            import logging
            logging.warning(f"Failed to update project tasks for workflow change: {e}")
    
    @transactional
    def check_and_update_project_completion(self, project_id, user_id=None):
        """Check if all tasks in a project are completed and update project status accordingly"""
        if not project_id:
            return
        
        try:
            project = self.project_repository.get_by_id_and_firm(project_id, firm_id=None)  # Allow any firm for this internal check
            if not project:
                return
            
            # Count total tasks and completed tasks
            from repositories.task_repository import TaskRepository
            task_repo = TaskRepository()
            project_tasks = task_repo.get_project_tasks(project_id, project.firm_id, include_completed=True)
            total_tasks = len(project_tasks)
            completed_tasks = len([t for t in project_tasks if t.status == 'Completed'])
            
            # If all tasks are completed, mark project as completed
            if total_tasks > 0 and completed_tasks == total_tasks and project.status != 'Completed':
                project.status = 'Completed'
                ActivityService.create_activity_log(
                    f'Project "{project.name}" automatically marked as completed (all tasks finished)',
                    user_id or 1,
                    project_id
                )
                db.session.commit()
            # If project was marked completed but has incomplete tasks, reactivate it
            elif project.status == 'Completed' and completed_tasks < total_tasks:
                project.status = 'Active'
                ActivityService.create_activity_log(
                    f'Project "{project.name}" reactivated (incomplete tasks detected)',
                    user_id or 1,
                    project_id
                )
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Error checking project completion for project {project_id}: {e}")
