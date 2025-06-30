"""
Task Repository for CPA WorkflowPilot
Provides data access layer for task-related operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import or_, and_

from src.shared.database.db_import import db
from .models import Task, Project
from src.shared.repositories import CachedRepository, PaginationResult


class TaskRepository(CachedRepository[Task]):
    """Repository for Task entity with caching support"""
    
    def __init__(self):
        super().__init__(Task, cache_ttl=300)  # 5 minute cache
    
    def get_filtered_tasks(self, firm_id: int, filters: Optional[Dict[str, Any]] = None, 
                          limit: Optional[int] = None) -> List[Task]:
        """Get tasks with various filters applied and optional limit"""
        query = self._build_filtered_query(firm_id, filters)
        
        # Order by due date and priority
        query = query.order_by(
            Task.due_date.asc().nullslast(),
            Task.priority.asc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_filtered_tasks_paginated(self, firm_id: int, page: int = 1, per_page: int = 50,
                                   filters: Optional[Dict[str, Any]] = None) -> PaginationResult:
        """Get tasks with various filters applied and pagination"""
        query = self._build_filtered_query(firm_id, filters)
        
        # Order by due date and priority
        query = query.order_by(
            Task.due_date.asc().nullslast(),
            Task.priority.asc()
        )
        
        total = query.count()
        pages = (total + per_page - 1) // per_page
        
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return PaginationResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_prev=page > 1,
            has_next=page < pages
        )
    
    def _build_filtered_query(self, firm_id: int, filters: Optional[Dict[str, Any]] = None):
        """Build a filtered query for tasks (shared logic)"""
        query = Task.query.outerjoin(Project).filter(
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        if filters:
            # Hide completed tasks by default
            if not filters.get('show_completed', False):
                query = query.filter(Task.status != 'Completed')
            
            # Apply multi-select filters
            if filters.get('status_filters'):
                query = query.filter(Task.status.in_(filters['status_filters']))
            
            if filters.get('priority_filters'):
                query = query.filter(Task.priority.in_(filters['priority_filters']))
            
            if filters.get('assignee_filters'):
                assignee_conditions = []
                if 'unassigned' in filters['assignee_filters']:
                    assignee_conditions.append(Task.assignee_id.is_(None))
                
                user_ids = [f for f in filters['assignee_filters'] if f != 'unassigned']
                if user_ids:
                    assignee_conditions.append(Task.assignee_id.in_(user_ids))
                
                if assignee_conditions:
                    query = query.filter(or_(*assignee_conditions))
            
            if filters.get('project_filters'):
                project_conditions = []
                if 'independent' in filters['project_filters']:
                    project_conditions.append(Task.project_id.is_(None))
                
                project_ids = [f for f in filters['project_filters'] if f != 'independent']
                if project_ids:
                    project_conditions.append(Task.project_id.in_(project_ids))
                
                if project_conditions:
                    query = query.filter(or_(*project_conditions))
        
        return query
    
    def get_project_tasks(self, project_id: int, firm_id: int, 
                         include_completed: bool = False) -> List[Task]:
        """Get all tasks for a specific project"""
        query = Task.query.join(Project).filter(
            Task.project_id == project_id,
            Project.firm_id == firm_id
        )
        
        if not include_completed:
            query = query.filter(Task.status != 'Completed')
        
        return query.order_by(Task.created_at.asc()).all()
    
    def get_user_tasks(self, user_id: int, firm_id: int, 
                      include_completed: bool = False) -> List[Task]:
        """Get all tasks assigned to a user"""
        query = Task.query.outerjoin(Project).filter(
            Task.assignee_id == user_id,
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        if not include_completed:
            query = query.filter(Task.status != 'Completed')
        
        return query.order_by(Task.due_date.asc().nullslast()).all()
    
    def get_overdue_tasks(self, firm_id: int) -> List[Task]:
        """Get all overdue tasks"""
        today = datetime.utcnow().date()
        
        return Task.query.outerjoin(Project).filter(
            Task.due_date < today,
            Task.status != 'Completed',
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(Task.due_date.asc()).all()
    
    def get_tasks_due_soon(self, firm_id: int, days: int = 3) -> List[Task]:
        """Get tasks due within specified days"""
        from datetime import timedelta
        
        today = datetime.utcnow().date()
        soon = today + timedelta(days=days)
        
        return Task.query.outerjoin(Project).filter(
            Task.due_date.between(today, soon),
            Task.status != 'Completed',
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(Task.due_date.asc()).all()
    
    def get_task_statistics(self, firm_id: int) -> Dict[str, int]:
        """Get task statistics"""
        total = self.count(firm_id=firm_id)
        not_started = self.count(firm_id=firm_id, status='Not Started')
        in_progress = self.count(firm_id=firm_id, status='In Progress')
        completed = self.count(firm_id=firm_id, status='Completed')
        
        today = datetime.utcnow().date()
        overdue = Task.query.outerjoin(Project).filter(
            Task.due_date < today,
            Task.status != 'Completed',
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).count()
        
        return {
            'total': total,
            'not_started': not_started,
            'in_progress': in_progress,
            'completed': completed,
            'overdue': overdue
        }
    
    def create_from_template(self, template_id: int, project_id: int, 
                           firm_id: int, user_id: int) -> Optional[Task]:
        """Create task from template"""
        from src.models import TemplateTask
        
        template = TemplateTask.query.get(template_id)
        if not template:
            return None
        
        task = Task(
            title=template.title,
            description=template.description,
            project_id=project_id,
            assignee_id=template.default_assignee_id,
            priority=template.priority,
            firm_id=firm_id,
            created_by=user_id,
            template_task_origin_id=template.id
        )
        
        db.session.add(task)
        # Note: Transaction commit is handled by service layer
        return task
    
    def bulk_update(self, task_ids: List[int], updates: Dict[str, Any], 
                   firm_id: int) -> Dict[str, Any]:
        """Bulk update multiple tasks"""
        tasks = Task.query.outerjoin(Project).filter(
            Task.id.in_(task_ids),
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).all()
        
        if not tasks:
            return {
                'success': False,
                'message': 'No valid tasks found'
            }
        
        valid_fields = self._filter_valid_fields(updates)
        updated_count = 0
        
        for task in tasks:
            task_updated = False
            for field, value in valid_fields.items():
                if hasattr(task, field):
                    setattr(task, field, value)
                    task_updated = True
            if task_updated:
                updated_count += 1
        
        # Note: Transaction commit is handled by service layer
        
        return {
            'success': True,
            'message': f'Successfully updated {updated_count} tasks',
            'updated_count': updated_count
        }
    
    def bulk_delete(self, task_ids: List[int], firm_id: int) -> Dict[str, Any]:
        """Bulk delete multiple tasks"""
        tasks = Task.query.outerjoin(Project).filter(
            Task.id.in_(task_ids),
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).all()
        
        if not tasks:
            return {
                'success': False,
                'message': 'No valid tasks found'
            }
        
        deleted_count = 0
        for task in tasks:
            db.session.delete(task)
            deleted_count += 1
        
        # Note: Transaction commit is handled by service layer
        
        return {
            'success': True,
            'message': f'Successfully deleted {deleted_count} tasks',
            'deleted_count': deleted_count
        }
    
    def get_tasks_by_firm(self, firm_id: int, limit: Optional[int] = None) -> List[Task]:
        """
        Get all tasks for a firm with proper ordering and optional limit
        WARNING: Use get_tasks_by_firm_paginated for large datasets
        """
        query = Task.query.outerjoin(Project).filter(
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(
            Task.due_date.asc().nullslast(),
            db.case(
                (Task.priority == 'High', 1),
                (Task.priority == 'Medium', 2),  
                (Task.priority == 'Low', 3),
                else_=4
            )
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_tasks_by_firm_paginated(self, firm_id: int, page: int = 1, per_page: int = 50) -> PaginationResult:
        """Get all tasks for a firm with pagination"""
        query = Task.query.outerjoin(Project).filter(
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(
            Task.due_date.asc().nullslast(),
            db.case(
                (Task.priority == 'High', 1),
                (Task.priority == 'Medium', 2),  
                (Task.priority == 'Low', 3),
                else_=4
            )
        )
        
        total = query.count()
        pages = (total + per_page - 1) // per_page
        
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return PaginationResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_prev=page > 1,
            has_next=page < pages
        )
    
    def get_recent_tasks(self, firm_id: int, limit: int = 5) -> List[Task]:
        """Get recent tasks for a firm"""
        return Task.query.outerjoin(Project).filter(
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(Task.created_at.desc()).limit(limit).all()
    
    def get_by_id_with_firm_access(self, task_id: int, firm_id: int) -> Optional[Task]:
        """Get task by ID with firm access verification"""
        return Task.query.outerjoin(Project).filter(
            Task.id == task_id,
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).first()
    
    def get_tasks_by_date_range(self, firm_id: int, start_date, end_date, limit: Optional[int] = None) -> List[Task]:
        """Get tasks with due dates within a specific date range - optimized for calendar view"""
        query = Task.query.outerjoin(Project).filter(
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.due_date.between(start_date, end_date)
        ).order_by(Task.due_date.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
