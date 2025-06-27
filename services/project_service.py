"""
Project service layer for business logic
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from flask import session
from core.db_import import db
from models import Project, Template, Task, Client, TaskStatus, TemplateTask, WorkType, User, ActivityLog
from repositories.project_repository import ProjectRepository
from utils.core import calculate_task_due_date, find_or_create_client
from utils.session_helpers import get_session_firm_id, get_session_user_id
from services.activity_logging_service import ActivityLoggingService as ActivityService
from events.publisher import publish_event
from events.schemas import ProjectCreatedEvent, ProjectUpdatedEvent

class ProjectService:
    """Service class for project-related business operations"""
    
    def __init__(self):
        self.project_repository = ProjectRepository()
    
    def get_projects_for_firm(self, firm_id: int) -> List[Project]:
        """Get all projects for a firm"""
        return self.project_repository.get_by_firm(firm_id)
    
    def get_project_by_id(self, project_id: int, firm_id: int) -> Optional[Project]:
        """Get a project by ID, ensuring it belongs to the firm"""
        return self.project_repository.get_by_id_and_firm(project_id, firm_id)
    

    def create_project_from_template(
        template_id: int,
        client_name: str,
        project_name: Optional[str],
        start_date: datetime.date,
        due_date: Optional[datetime.date],
        priority: str = 'Medium',
        task_dependency_mode: bool = False,
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new project from a template
        
        Returns:
            Dict with 'success', 'project_id', 'message', and optionally 'new_client'
        """
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            # Find or create client
            client = find_or_create_client(client_name, firm_id)
            was_new_client = client.email is None
            
            # Get template to access work type
            template = Template.query.get(template_id)
            if not template:
                return {'success': False, 'message': 'Template not found'}
            
            # Auto-create work type from template if needed
            work_type_id = template.create_work_type_from_template()
            
            # Get the default (first) status for the work type
            default_status = TaskStatus.query.filter_by(
                work_type_id=work_type_id,
                is_default=True
            ).first()
            
            # Inherit sequential flag from template
            inherited_task_dependency_mode = template.task_dependency_mode if template else task_dependency_mode
            
            # Create project
            project = Project(
                name=project_name or f"{client.name} - {template.name}",
                client_id=client.id,
                work_type_id=work_type_id,
                current_status_id=default_status.id if default_status else None,
                start_date=start_date,
                due_date=due_date,
                priority=priority,
                task_dependency_mode=inherited_task_dependency_mode,
                firm_id=firm_id,
                template_origin_id=template_id
            )
            db.session.add(project)
            db.session.flush()
            
            # Create tasks from template
            tasks_created = ProjectService._create_tasks_from_template(
                project, template, start_date, firm_id
            )
            
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='create',
                details=f'Created project "{project.name}" with {tasks_created} tasks'
            )
            
            return {
                'success': True,
                'project_id': project.id,
                'message': f'Project "{project.name}" created successfully',
                'new_client': was_new_client,
                'tasks_created': tasks_created
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error creating project: {str(e)}'}
    

    def _create_tasks_from_template(
        project: Project, 
        template: Template, 
        start_date: datetime.date,
        firm_id: int
    ) -> int:
        """Create tasks from template for a project"""
        tasks_created = 0
        
        for template_task in template.template_tasks:
            # Calculate due date
            task_due_date = calculate_task_due_date(start_date, template_task)
            
            # Determine status: use template status if available, otherwise work type default
            status_id = None
            if template_task.default_status_id:
                status_id = template_task.default_status_id
            elif template.work_type_id:
                # Get default status for this work type
                default_status = TaskStatus.query.filter_by(
                    work_type_id=template.work_type_id,
                    is_default=True
                ).first()
                if default_status:
                    status_id = default_status.id
            
            task = Task(
                title=template_task.title,
                description=template_task.description,
                due_date=task_due_date,
                priority=template_task.default_priority or 'Medium',
                estimated_hours=template_task.estimated_hours,
                project_id=project.id,
                assignee_id=template_task.default_assignee_id,
                template_task_origin_id=template_task.id,
                status_id=status_id,
                dependencies=template_task.dependencies,
                firm_id=firm_id
            )
            db.session.add(task)
            tasks_created += 1
            
        return tasks_created
    

    def update_project(
        project_id: int,
        name: str,
        start_date: datetime.date,
        due_date: Optional[datetime.date],
        priority: str,
        status: str,
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update an existing project"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            project = ProjectService.get_project_by_id(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found'}
            
            # Update project fields
            project.name = name
            project.start_date = start_date
            project.due_date = due_date
            project.priority = priority
            project.status = status
            
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='update',
                details=f'Updated project "{project.name}"'
            )
            
            return {'success': True, 'message': 'Project updated successfully'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating project: {str(e)}'}
    

    def delete_project(self, project_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete a project and all associated data"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            project = ProjectService.get_project_by_id(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found'}
            
            project_name = project.name
            client_name = project.client_name
            
            # Count tasks for logging
            task_count = len(project.tasks)
            
            # Delete associated tasks (cascade should handle this but be explicit)
            for task in project.tasks:
                db.session.delete(task)
            
            # Delete the project
            db.session.delete(project)
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='delete',
                details=f'Deleted project "{project_name}" for {client_name} with {task_count} tasks'
            )
            
            return {
                'success': True,
                'message': f'Project "{project_name}" and {task_count} associated tasks deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error deleting project: {str(e)}'}
    

    def move_project_status(
        project_id: int, 
        status_id: str, 
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Move project to a different status (for Kanban)"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            project = ProjectService.get_project_by_id(project_id, firm_id)
            if not project:
                return {'success': False, 'message': 'Project not found'}
            
            # Handle special "completed" status
            if status_id == 'completed':
                project.status = 'Completed'
                project.current_status_id = None
                status_name = 'Completed'
                
                # Mark ALL tasks as completed
                tasks_updated = 0
                for task in project.tasks:
                    if task.status != 'Completed':
                        task.status = 'Completed'
                        task.completed_at = datetime.utcnow()
                        tasks_updated += 1
                
                
            else:
                # The status_id is actually a TemplateTask ID, find the corresponding TaskStatus
                from models import TemplateTask
                template_task = TemplateTask.query.get(status_id)
                if not template_task:
                    return {'success': False, 'message': f'Template task {status_id} not found'}
                
                # Update project workflow status to reflect the new kanban column
                if template_task.default_status_id:
                    status = TaskStatus.query.get(template_task.default_status_id)
                    if status:
                        project.current_status_id = status.id
                        status_name = status.name
                    else:
                        project.current_status_id = None
                        status_name = template_task.title
                else:
                    project.current_status_id = None
                    status_name = template_task.title
                
                # Implement logical workflow progression: complete all previous stages
                # Get all template tasks ordered by workflow
                all_template_tasks = TemplateTask.query.filter_by(
                    template_id=template_task.template_id
                ).order_by(TemplateTask.workflow_order.asc()).all()
                
                # Find position of current template task
                current_position = 0
                for i, tt in enumerate(all_template_tasks):
                    if tt.id == template_task.id:
                        current_position = i
                        break
                
                # Update task statuses based on workflow progression
                for i, tt in enumerate(all_template_tasks):
                    for task in project.tasks:
                        if task.template_task_origin_id == tt.id:
                            if i < current_position:
                                # Previous stages: mark as completed
                                if task.status != 'Completed':
                                    task.status = 'Completed'
                                    task.completed_at = datetime.utcnow()
                            elif i == current_position:
                                # Current stage: mark as in progress
                                if task.status != 'In Progress':
                                    task.status = 'In Progress'
                            else:
                                # Future stages: reset to "Not Started"
                                if task.status != 'Not Started':
                                    task.status = 'Not Started'
                                    task.completed_at = None
                            break
                
                project.status = 'Active'
            
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'Moved project "{project.name}" to status: {status_name}',
                user_id=session.get('user_id'),
                project_id=project.id
            )
            
            return {
                'success': True,
                'message': f'Project moved to {status_name}',
                'project_progress': project.progress_percentage,
                'completed_tasks': len([t for t in project.tasks if t.status == 'Completed']),
                'total_tasks': len(project.tasks)
            }
            
        except Exception as e:
            import traceback
            db.session.rollback()
            error_details = traceback.format_exc()
            print(f"ProjectService.move_project_status error: {error_details}")
            return {'success': False, 'message': f'Error moving project: {str(e)}'}
    

    def get_project_statistics(self, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get project statistics for dashboard"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        projects = ProjectService.get_projects_for_firm(firm_id)
        
        stats = {
            'total': len(projects),
            'active': len([p for p in projects if p.status == 'Active']),
            'completed': len([p for p in projects if p.status == 'Completed']),
            'on_hold': len([p for p in projects if p.status == 'On Hold']),
            'overdue': len([p for p in projects if p.is_overdue]),
        }
        
        return stats
    

    def get_project_workflow_progress(self, project_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get project workflow progress (OpenProject-inspired)"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        project = ProjectService.get_project_by_id(project_id, firm_id)
        if not project:
            return {'success': False, 'message': 'Project not found'}
        
        # Calculate workflow progress
        total_tasks = len(project.tasks)
        completed_tasks = len([t for t in project.tasks if t.status == 'Completed'])
        in_progress_tasks = len([t for t in project.tasks if t.status == 'In Progress'])
        blocked_tasks = len([t for t in project.tasks if hasattr(t, 'is_blocked') and t.is_blocked])
        
        # Calculate completion percentage
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Determine project health status
        health_status = 'healthy'
        if blocked_tasks > 0:
            health_status = 'blocked'
        elif project.is_overdue:
            health_status = 'at_risk'
        elif completion_percentage < 25 and project.due_date and (project.due_date - date.today()).days < 7:
            health_status = 'behind_schedule'
        
        return {
            'success': True,
            'project_name': project.name,
            'client_name': project.client_name,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'blocked_tasks': blocked_tasks,
            'completion_percentage': round(completion_percentage, 1),
            'health_status': health_status,
            'days_remaining': (project.due_date - date.today()).days if project.due_date else None,
            'is_overdue': project.is_overdue
        }
    

    def get_firm_workflow_summary(self, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get firm-wide workflow summary (OpenProject-inspired dashboard)"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        projects = ProjectService.get_projects_for_firm(firm_id)
        
        # Project health distribution
        healthy_projects = 0
        at_risk_projects = 0
        blocked_projects = 0
        
        total_completion = 0
        
        for project in projects:
            if project.status != 'Completed':
                progress = ProjectService.get_project_workflow_progress(project.id, firm_id)
                if progress['success']:
                    total_completion += progress['completion_percentage']
                    if progress['health_status'] == 'healthy':
                        healthy_projects += 1
                    elif progress['health_status'] in ['at_risk', 'behind_schedule']:
                        at_risk_projects += 1
                    elif progress['health_status'] == 'blocked':
                        blocked_projects += 1
        
        active_projects = len([p for p in projects if p.status == 'Active'])
        avg_completion = (total_completion / active_projects) if active_projects > 0 else 0
        
        return {
            'total_projects': len(projects),
            'active_projects': active_projects,
            'completed_projects': len([p for p in projects if p.status == 'Completed']),
            'healthy_projects': healthy_projects,
            'at_risk_projects': at_risk_projects,
            'blocked_projects': blocked_projects,
            'average_completion': round(avg_completion, 1),
            'overdue_projects': len([p for p in projects if p.is_overdue])
        }