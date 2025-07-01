"""
ViewsService: Handles business logic for view-related operations (kanban, reports, etc.)
"""

from datetime import date, timedelta
from core.db_import import db
from models import Project, Task, User
from services.worktype_service import WorkTypeService
from services.project_service import ProjectService
from services.user_service import UserService


class ViewsService:
    @staticmethod
    def get_kanban_data(firm_id, work_type_filter=None, priority_filter=None, due_filter=None):
        """Get kanban board data with filtering"""
        try:
            # Create WorkTypeService instance for this request scope
            worktype_service = WorkTypeService()
            
            # Get work types using WorkTypeService
            work_types_result = worktype_service.get_work_types_for_firm(firm_id, active_only=True)
            if not work_types_result['success']:
                return work_types_result
            
            work_types = work_types_result['work_types']
            
            # Get current work type and kanban columns
            current_work_type = None
            kanban_columns = []
            
            if work_type_filter:
                work_type_result = worktype_service.get_work_type_by_id(work_type_filter, firm_id)
                if work_type_result['success']:
                    current_work_type = work_type_result['work_type']
                    
                    # Get task statuses as kanban columns
                    statuses_result = worktype_service.get_task_statuses_for_work_type(current_work_type.id)
                    if statuses_result['success']:
                        kanban_columns = statuses_result['statuses']
            
            # Get all projects for the firm using ProjectService
            project_service = ProjectService()
            projects = project_service.get_projects_for_firm(firm_id)
            
            # Apply work type filter
            if work_type_filter and current_work_type:
                projects = [p for p in projects if p.work_type_id == current_work_type.id]
            
            # Apply priority filter
            if priority_filter:
                projects = [p for p in projects if p.priority == priority_filter]
            
            # Apply due date filters
            if due_filter:
                today = date.today()
                if due_filter == 'overdue':
                    projects = [p for p in projects if p.due_date and p.due_date < today]
                elif due_filter == 'today':
                    projects = [p for p in projects if p.due_date == today]
                elif due_filter == 'this_week':
                    week_end = today + timedelta(days=7)
                    projects = [p for p in projects if p.due_date and today <= p.due_date <= week_end]
            
            return {
                'success': True,
                'work_types': work_types,
                'current_work_type': current_work_type,
                'kanban_columns': kanban_columns,
                'projects': projects
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving kanban data: {str(e)}'
            }
    
    @staticmethod
    def get_time_tracking_data(firm_id, start_date=None, end_date=None, user_id=None, project_id=None):
        """Get time tracking report data with filtering"""
        try:
            # Use DashboardAggregatorService for time tracking logic
            from services.dashboard_aggregator_service import DashboardAggregatorService
            dashboard_service = DashboardAggregatorService()
            
            # Get base report data
            report_data = dashboard_service.get_time_tracking_report(firm_id, start_date, end_date)
            
            # Get detailed tasks (not the count)
            tasks = report_data.get('detailed_tasks', [])
            
            # Apply additional filters (tasks are dictionaries from detailed_tasks)
            if user_id:
                # Need to filter based on assignee name or get user name
                from repositories.user_repository import UserRepository
                user_repo = UserRepository()
                user = user_repo.get_by_id(int(user_id))
                user_name = user.name if user else None
                if user_name:
                    tasks = [task for task in tasks if task.get('assignee') == user_name]
            
            if project_id:
                # Need to filter based on project name
                from repositories.project_repository import ProjectRepository
                project_repo = ProjectRepository()
                project = project_repo.get_by_id(int(project_id))
                project_name = project.name if project else None
                if project_name:
                    tasks = [task for task in tasks if task.get('project') == project_name]
            
            # Recalculate statistics for filtered results
            if user_id or project_id:
                total_hours = sum(task.get('hours', 0) for task in tasks)
                billable_hours = sum(task.get('hours', 0) for task in tasks if task.get('is_billable', True))
                total_revenue = sum(task.get('hours', 0) * task.get('hourly_rate', 0) for task in tasks if task.get('is_billable', True))
            else:
                total_hours = report_data['summary']['total_hours']
                billable_hours = report_data['summary']['billable_hours']
                total_revenue = report_data['summary']['total_revenue']
            
            # Get filter options using services
            user_service = UserService()
            users = user_service.get_users_by_firm(firm_id)
            project_service = ProjectService()
            projects = project_service.get_projects_for_firm(firm_id)
            
            return {
                'success': True,
                'tasks': tasks,
                'users': users,
                'projects': projects,
                'total_hours': total_hours,
                'billable_hours': billable_hours,
                'total_revenue': total_revenue
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving time tracking data: {str(e)}'
            }
    
    @staticmethod
    def organize_projects_by_kanban_columns(projects, kanban_columns):
        """Organize projects into kanban columns"""
        try:
            from collections import namedtuple
            
            # Create wrapper objects for template compatibility
            Column = namedtuple('Column', ['id', 'title', 'order'])
            
            # Convert TaskStatus objects to Column objects
            wrapped_columns = []
            for status in kanban_columns:
                wrapped_columns.append(Column(status.id, status.name, status.position))
            
            # Initialize columns
            projects_by_column = {}
            project_counts = {}
            
            for column in wrapped_columns:
                projects_by_column[column.id] = []
                project_counts[column.id] = 0
            
            # Add completed column for any completed projects
            projects_by_column['completed'] = []
            project_counts['completed'] = 0
            
            # Organize projects into columns
            for project in projects:
                # Check if project is completed first
                if project.status == 'Completed':
                    projects_by_column['completed'].append(project)
                    project_counts['completed'] += 1
                elif project.current_status_id:
                    # Map project's current_status_id to the corresponding TaskStatus column
                    column_found = False
                    for column in wrapped_columns:
                        if project.current_status_id == column.id:
                            projects_by_column[column.id].append(project)
                            project_counts[column.id] += 1
                            column_found = True
                            break
                    
                    # If no specific column found, put in first column
                    if not column_found and wrapped_columns:
                        first_column = wrapped_columns[0]
                        projects_by_column[first_column.id].append(project)
                        project_counts[first_column.id] += 1
                else:
                    # No current status - put in first column (default status)
                    if wrapped_columns:
                        first_column = wrapped_columns[0]
                        projects_by_column[first_column.id].append(project)
                        project_counts[first_column.id] += 1
            
            return {
                'success': True,
                'kanban_columns': wrapped_columns,
                'projects_by_column': projects_by_column,
                'project_counts': project_counts
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error organizing kanban columns: {str(e)}'
            }