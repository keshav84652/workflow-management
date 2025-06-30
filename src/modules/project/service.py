"""
ProjectService: Handles all business logic for project operations.
"""

from typing import Dict, Any, Optional, List
from src.shared.database.db_import import db
from .models import Project, Task, WorkType
from ..client.models import Client
from src.models.auth import User
# ActivityService import removed to break circular dependency
from src.shared.base import BaseService, transactional
from .interface import IProjectService
from src.shared.exceptions import ValidationError, NotFoundError, ExternalServiceError
from .repository import ProjectRepository


class ProjectService(BaseService):
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        # Proper dependency injection - repository is required
        self.project_repository = project_repository
    def get_projects_for_firm(self, firm_id, include_inactive=False):
        """Get all projects for a firm as DTOs to prevent N+1 queries"""
        projects = self.project_repository.get_by_firm(firm_id, include_inactive)
        
        # Convert to DTOs to prevent N+1 queries in templates
        project_dtos = []
        for project in projects:
            project_dto = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                'due_date': project.due_date.strftime('%Y-%m-%d') if project.due_date else None,
                'client_id': project.client_id,
                'client_name': project.client.name if project.client else 'No Client',
                'work_type_id': project.work_type_id,
                'work_type_name': project.work_type.name if project.work_type else None,
                'firm_id': project.firm_id,
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else None,
                'is_completed': project.status == 'Completed',
                'current_status_id': project.current_status_id,
                'progress_percentage': project.progress_percentage if hasattr(project, 'progress_percentage') else 0
            }
            project_dtos.append(project_dto)
        
        return project_dtos
    
    def get_project_by_id_and_firm(self, project_id, firm_id):
        """Get project by ID with firm access check"""
        project = self.project_repository.get_by_id_and_firm(project_id, firm_id)
        if not project:
            return None
        
        # Return DTO instead of raw model to prevent N+1 queries in templates
        return {
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
            'due_date': project.due_date.strftime('%Y-%m-%d') if project.due_date else None,
            'client_id': project.client_id,
            'client_name': project.client.name if project.client else 'No Client',
            'work_type_id': project.work_type_id,
            'work_type_name': project.work_type.name if project.work_type else None,
            'firm_id': project.firm_id,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else None,
            'is_completed': project.status == 'Completed',
            'current_status_id': project.current_status_id,
            'current_workflow_status_name': project.current_workflow_status_name if hasattr(project, 'current_workflow_status_name') else None
        }
    
    def get_project_progress(self, project_id, firm_id):
        """Get project progress with access check"""
        project = self.get_project_by_id_and_firm(project_id, firm_id)
        if not project:
            return {
                'success': False,
                'message': 'Project not found or access denied'
            }
        
        from .task_repository import TaskRepository
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
    def create_project(self, name, description=None, client_id=None, work_type_id=None, firm_id=None, user_id=None) -> Dict[str, Any]:
        """Create a new project
        
        Args:
            name: Project name
            description: Optional project description 
            client_id: Optional client ID
            work_type_id: Optional work type ID
            firm_id: Firm ID
            user_id: User ID for activity logging
            
        Returns:
            Dict with created project data
            
        Raises:
            ValidationError: If input validation fails
            NotFoundError: If client or work type not found
        """
        # Validate input
        if not name or not name.strip():
            raise ValidationError("Project name is required")
        
        # Verify client belongs to firm
        if client_id:
            client = Client.query.filter_by(id=client_id, firm_id=firm_id).first()
            if not client:
                raise NotFoundError(f"Client {client_id} not found or doesn't belong to firm {firm_id}")
        
        # Verify work type belongs to firm
        if work_type_id:
            work_type = WorkType.query.filter_by(id=work_type_id, firm_id=firm_id).first()
            if not work_type:
                raise NotFoundError(f"Work type {work_type_id} not found or doesn't belong to firm {firm_id}")
        
        # Create project
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
            from .models import TaskStatus
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
        
        # Log activity - direct import to avoid circular dependency
        try:
            from src.shared.services.activity_service import ActivityService
            activity_service = ActivityService()
            activity_service.log_entity_operation(
                entity_type='PROJECT',
                operation='CREATE',
                entity_id=project.id,
                entity_name=project.name,
                details=f'Project created for client: {client.name if client_id and Client.query.get(client_id) else "No client"}',
                user_id=user_id
            )
        except (ImportError, Exception):
            pass  # ActivityService not available or failed
        
        # Publish project creation event
        try:
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
        except Exception:
            pass  # Event publishing is optional
        
        # Return DTO with created project data (not the old success/failure dictionary)
        return {
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'client_id': project.client_id,
            'work_type_id': project.work_type_id,
            'firm_id': project.firm_id,
            'current_status_id': project.current_status_id,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else None
        }
    
    @transactional
    def create_project_from_template(self, template_id, client_name, project_name, start_date, due_date=None, priority='Medium', task_dependency_mode=False, firm_id=None, user_id=None):
        """Create a project from a template"""
        try:
            # For now, this can just call the regular create_project method
            # In the future, this could be enhanced to use template-specific logic
            return self.create_project(
                name=project_name,
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
            # Get the raw model for updating (not DTO)
            project = self.project_repository.get_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            # Update allowed fields
            if 'name' in update_data:
                project.name = update_data['name']
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
            # Get the raw model for deletion (not DTO)
            project = self.project_repository.get_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            # Check if project has tasks  
            from .task_repository import TaskRepository
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
            # Get raw model for updates, not DTO
            project = self.project_repository.get_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            old_status = project.status
            project.status = new_status
            
            db.session.commit()
            
            # Log activity - direct import to avoid circular dependency
            try:
                from src.shared.services.activity_service import ActivityService
                ActivityService.log_entity_operation(
                    entity_type='PROJECT',
                    operation='UPDATE',
                    entity_id=project.id,
                    entity_name=project.name,
                    details=f'Status changed from "{old_status}" to "{new_status}"',
                    user_id=user_id
                )
            except ImportError:
                pass  # ActivityService not available
            
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
        projects = self.project_repository.get_by_firm(firm_id, include_inactive=False)
        
        # Return DTOs to prevent N+1 queries in templates
        project_dtos = []
        for project in projects:
            project_dto = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'client_id': project.client_id,
                'client_name': project.client.name if project.client else 'No Client',
                'work_type_id': project.work_type_id,
                'work_type_name': project.work_type.name if project.work_type else None,
                'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else None,
                'is_completed': project.status == 'Completed'
            }
            project_dtos.append(project_dto)
        
        return project_dtos
    
    def get_project_by_id(self, project_id, firm_id):
        """Get project by ID for firm"""
        return self.get_project_by_id_and_firm(project_id, firm_id)
    
    # Removed duplicate method - using full implementation below
    
    @transactional
    def move_project_status(self, project_id, status_id, firm_id, user_id=None):
        """Move project to different status for Kanban board"""
        try:
            # Get raw model for updates, not DTO
            project = self.project_repository.get_by_id_and_firm(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found or access denied'}
            
            old_status = project.current_workflow_status_name
            
            # Handle special completed column
            if status_id == 'completed':
                project.status = 'Completed'
                
                # Find terminal status for this work type
                if project.work_type_id:
                    from .models import TaskStatus
                    terminal_status = TaskStatus.query.filter_by(
                        work_type_id=project.work_type_id,
                        is_terminal=True
                    ).first()
                    if terminal_status:
                        project.current_status_id = terminal_status.id
                
                # Publish event for task completion (replaces direct task modification)
                try:
                    from src.shared.events.schemas import ProjectCompletedEvent
                    from src.shared.events.publisher import publish_event
                    
                    completion_event = ProjectCompletedEvent(
                        project_id=project.id,
                        project_name=project.name,
                        firm_id=firm_id,
                        work_type_id=project.work_type_id,
                        user_id=user_id
                    )
                    publish_event(completion_event)
                except Exception as event_error:
                    print(f"Failed to publish project completed event: {event_error}")
                
                message = 'Project completed'
            else:
                # status_id should be a TaskStatus ID
                try:
                    status_id = int(status_id)
                    from .models import TaskStatus
                    task_status = TaskStatus.query.filter_by(
                        id=status_id,
                        work_type_id=project.work_type_id
                    ).first()
                    
                    if not task_status:
                        return {'success': False, 'message': 'Invalid status for this project type'}
                    
                    old_status_id = project.current_status_id
                    old_status = TaskStatus.query.get(old_status_id) if old_status_id else None
                    
                    project.current_status_id = status_id
                    project.status = 'Active'  # Keep as active unless completed
                    
                    # Publish event for task status updates (replaces direct cross-domain manipulation)
                    try:
                        from src.shared.events.schemas import ProjectWorkflowAdvancedEvent
                        from src.shared.events.publisher import publish_event
                        
                        workflow_event = ProjectWorkflowAdvancedEvent(
                            project_id=project.id,
                            project_name=project.name,
                            firm_id=firm_id,
                            old_status_id=old_status_id,
                            new_status_id=status_id,
                            old_status_name=old_status.name if old_status else None,
                            new_status_name=task_status.name,
                            work_type_id=project.work_type_id,
                            user_id=user_id
                        )
                        publish_event(workflow_event)
                    except Exception as event_error:
                        print(f"Failed to publish workflow advanced event: {event_error}")
                    
                    message = f'Project moved to {task_status.name}'
                    
                except (ValueError, TypeError):
                    return {'success': False, 'message': 'Invalid status ID format'}
            
            db.session.commit()
            
            # Log activity if user_id provided
            if user_id:
                try:
                    from src.shared.services.activity_service import ActivityService
                    ActivityService.log_entity_operation(
                        entity_type='PROJECT',
                        operation='STATUS_MOVE',
                        entity_id=project.id,
                        entity_name=project.name,
                        details=f'Moved from "{old_status}" to "{project.current_workflow_status_name}" via Kanban',
                        user_id=user_id
                    )
                except ImportError:
                    pass  # ActivityService not available
            
            # Calculate updated progress for response  
            from .task_repository import TaskRepository
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
    
    def get_kanban_view_data(self, firm_id: int) -> Dict[str, Any]:
        """
        Get data formatted for Kanban view
        
        Args:
            firm_id: Firm ID to get data for
            
        Returns:
            Dict with kanban view data structure
            
        Raises:
            ExternalServiceError: If data retrieval fails
        """
        try:
            from .task_service import TaskService
            from src.shared.exceptions import ExternalServiceError
            
            task_service = TaskService()
            
            # Get all projects for kanban display (as DTOs)
            projects = self.get_active_projects(firm_id)
            
            # Get all tasks grouped by project and status
            all_tasks = task_service.get_tasks_for_kanban(firm_id)
            
            # Organize projects by their current workflow status
            from .models import TaskStatus, WorkType
            
            # Get all work types for this firm to build columns
            work_types = WorkType.query.filter_by(firm_id=firm_id).all()
            kanban_columns = {}
            
            for work_type in work_types:
                statuses = TaskStatus.query.filter_by(
                    work_type_id=work_type.id
                ).order_by(TaskStatus.position.asc()).all()
                
                for status in statuses:
                    column_key = f"status_{status.id}"
                    kanban_columns[column_key] = {
                        'id': status.id,
                        'title': status.name,
                        'work_type': work_type.name,
                        'projects': [],
                        'color': status.color or 'blue',
                        'position': status.position
                    }
            
            # Add completed column
            kanban_columns['completed'] = {
                'id': 'completed',
                'title': 'Completed',
                'work_type': 'All',
                'projects': [],
                'color': 'green',
                'position': 999
            }
            
            # Categorize projects by their current status
            for project in projects:
                if project['is_completed']:
                    kanban_columns['completed']['projects'].append(project)
                elif project.get('current_status_id'):
                    column_key = f"status_{project['current_status_id']}"
                    if column_key in kanban_columns:
                        kanban_columns[column_key]['projects'].append(project)
                else:
                    # Project without status - put in first available column
                    if kanban_columns:
                        first_column = min(kanban_columns.keys(), 
                                          key=lambda k: kanban_columns[k]['position'])
                        kanban_columns[first_column]['projects'].append(project)
            
            # Sort columns by position
            sorted_columns = dict(sorted(
                kanban_columns.items(),
                key=lambda x: x[1]['position']
            ))
            
            return {
                'success': True,
                'columns': sorted_columns,
                'total_projects': len(projects),
                'view_type': 'kanban'
            }
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to get kanban view data: {str(e)}")
    
    # REMOVED: _update_project_tasks_for_workflow_change
    # This method violated domain boundaries by directly manipulating Task models.
    # It has been replaced by the event-driven ProjectWorkflowTaskUpdateHandler
    # which responds to ProjectWorkflowAdvancedEvent to update task statuses.
    # This maintains proper domain separation while achieving the same functionality.
    
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
            from .task_repository import TaskRepository
            task_repo = TaskRepository()
            project_tasks = task_repo.get_project_tasks(project_id, project.firm_id, include_completed=True)
            total_tasks = len(project_tasks)
            completed_tasks = len([t for t in project_tasks if t.status == 'Completed'])
            
            # If all tasks are completed, mark project as completed
            if total_tasks > 0 and completed_tasks == total_tasks and project.status != 'Completed':
                project.status = 'Completed'
                try:
                    from src.shared.services.activity_service import ActivityService
                    ActivityService.create_activity_log(
                        f'Project "{project.name}" automatically marked as completed (all tasks finished)',
                        user_id or 1,
                        project_id
                    )
                except ImportError:
                    pass  # ActivityService not available
                db.session.commit()
            # If project was marked completed but has incomplete tasks, reactivate it
            elif project.status == 'Completed' and completed_tasks < total_tasks:
                project.status = 'Active'
                try:
                    from src.shared.services.activity_service import ActivityService
                    ActivityService.create_activity_log(
                        f'Project "{project.name}" reactivated (incomplete tasks detected)',
                        user_id or 1,
                        project_id
                    )
                except ImportError:
                    pass  # ActivityService not available
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Error checking project completion for project {project_id}: {e}")
    
    def get_project_statistics(self, firm_id: int) -> dict:
        """Get project statistics for dashboard"""
        try:
            from .models import Project
            
            total = Project.query.filter_by(firm_id=firm_id).count()
            active = Project.query.filter_by(firm_id=firm_id, status='Active').count()
            completed = Project.query.filter_by(firm_id=firm_id, status='Completed').count()
            
            return {
                'success': True,
                'statistics': {
                    'total': total,
                    'active': active,
                    'completed': completed
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get project statistics: {str(e)}',
                'statistics': {}
            }
    
    def get_projects_by_firm(self, firm_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get all projects for a firm"""
        try:
            from .models import Project, Client
            
            query = db.session.query(Project).outerjoin(Client).filter(
                Project.firm_id == firm_id
            ).order_by(Project.created_at.desc())
            
            projects = []
            for project in query.all():
                project_dict = {
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                    'due_date': project.due_date.strftime('%Y-%m-%d') if project.due_date else None,
                    'client_id': project.client_id,
                    'client_name': project.client.name if project.client else 'No Client',
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M'),
                    'is_completed': project.status == 'Completed'
                }
                projects.append(project_dict)
            
            return {
                'success': True,
                'projects': projects
            }
        except Exception as e:
            return {
                'success': False,
                'projects': [],
                'message': str(e)
            }
    
    def get_recent_projects(self, firm_id: int, limit: int = 5) -> dict:
        """Get recent projects for dashboard"""
        try:
            from .models import Project, Client
            from datetime import datetime, timedelta
            
            # Get projects created in the last 60 days
            sixty_days_ago = datetime.now() - timedelta(days=60)
            
            query = db.session.query(Project).outerjoin(Client).filter(
                Project.firm_id == firm_id,
                Project.created_at >= sixty_days_ago
            ).order_by(Project.created_at.desc()).limit(limit)
            
            projects = []
            for project in query.all():
                project_dict = {
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'client_name': project.client.name if project.client else 'No Client',
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M')
                }
                projects.append(project_dict)
            
            return {
                'success': True,
                'projects': projects
            }
        except Exception as e:
            return {
                'success': False,
                'projects': [],
                'message': str(e)
            }

    def get_tasks_by_project(self, project_id: int) -> List[Task]:
        """Get all tasks for a specific project"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.due_date.asc()).all()
    
    def get_activity_logs_for_project(self, project_id: int, limit: int = 10) -> List['ActivityLog']:
        """Get recent activity logs for a project"""
        from src.models.auth import ActivityLog
        return ActivityLog.query.filter_by(project_id=project_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_project_tasks_for_dependency(self, project_id: int) -> List[Task]:
        """Get tasks for dependency calculations"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.title).all()
    
    def search_projects(self, firm_id: int, query: str, limit: int = 20):
        """Search projects by name and description"""
        try:
            projects = self.project_repository.search_projects(firm_id, query, limit)
            return {
                'success': True,
                'projects': [self._project_to_dict(project) for project in projects]
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'projects': []
            }
    
    def _project_to_dict(self, project):
        """Convert project model to dictionary"""
        return {
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'client_name': project.client.name if project.client else None,
            'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else None
        }
    
