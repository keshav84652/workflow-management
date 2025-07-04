"""
Project Repository for CPA WorkflowPilot
Provides data access layer for project-related operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import or_, and_

from src.shared.database.db_import import db
from .models import Project
from src.shared.repositories import CachedRepository, PaginationResult


class ProjectRepository(CachedRepository[Project]):
    """Repository for Project entity with caching support"""
    
    def __init__(self):
        super().__init__(Project, cache_ttl=300)  # 5 minute cache
    
    def get_by_firm(self, firm_id: int, include_inactive: bool = False, limit: Optional[int] = None) -> List[Project]:
        """Get all projects for a firm with optional limit"""
        query = Project.query.filter(Project.firm_id == firm_id)
        
        if not include_inactive:
            query = query.filter(Project.status != 'Completed')
        
        query = query.order_by(Project.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_by_firm_paginated(self, firm_id: int, page: int = 1, per_page: int = 50, 
                             include_inactive: bool = False) -> PaginationResult:
        """Get projects for a firm with pagination"""
        query = Project.query.filter(Project.firm_id == firm_id)
        
        if not include_inactive:
            query = query.filter(Project.status != 'Completed')
        
        query = query.order_by(Project.created_at.desc())
        
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
    
    def get_by_client(self, client_id: int, firm_id: int, include_completed: bool = False) -> List[Project]:
        """Get all projects for a specific client"""
        query = Project.query.filter(
            Project.client_id == client_id,
            Project.firm_id == firm_id
        )
        
        if not include_completed:
            query = query.filter(Project.status != 'Completed')
        
        return query.order_by(Project.created_at.desc()).all()
    
    def get_by_status(self, firm_id: int, status: str) -> List[Project]:
        """Get projects by status"""
        return Project.query.filter(
            Project.firm_id == firm_id,
            Project.status == status
        ).order_by(Project.created_at.desc()).all()
    
    def get_kanban_data(self, firm_id: int) -> Dict[str, List[Project]]:
        """Get projects organized by status for kanban view"""
        projects = self.get_by_firm(firm_id, include_inactive=True)
        
        kanban_data = {
            'not_started': [],
            'in_progress': [],
            'review': [],
            'completed': []
        }
        
        for project in projects:
            # Map status to kanban columns
            if project.current_status_id == 1:  # Not Started
                kanban_data['not_started'].append(project)
            elif project.current_status_id == 2:  # In Progress
                kanban_data['in_progress'].append(project)
            elif project.current_status_id == 3:  # Review
                kanban_data['review'].append(project)
            elif project.current_status_id == 4:  # Completed
                kanban_data['completed'].append(project)
            else:
                # Default to not_started for unknown status
                kanban_data['not_started'].append(project)
        
        return kanban_data
    
    def get_project_statistics(self, firm_id: int) -> Dict[str, int]:
        """Get project statistics"""
        total = self.count(firm_id=firm_id)
        not_started = self.count(firm_id=firm_id, current_status_id=1)
        in_progress = self.count(firm_id=firm_id, current_status_id=2)
        review = self.count(firm_id=firm_id, current_status_id=3)
        completed = self.count(firm_id=firm_id, current_status_id=4)
        
        return {
            'total': total,
            'not_started': not_started,
            'in_progress': in_progress,
            'review': review,
            'completed': completed
        }
    
    def get_by_id_and_firm(self, project_id: int, firm_id: int) -> Optional[Project]:
        """Get project by ID ensuring it belongs to the firm"""
        return Project.query.filter(
            Project.id == project_id,
            Project.firm_id == firm_id
        ).first()
    
    def update_status(self, project_id: int, firm_id: int, status_id: int) -> Optional[Project]:
        """Update project status"""
        project = self.get_by_id_and_firm(project_id, firm_id)
        if not project:
            return None
        
        project.current_status_id = status_id
        project.updated_at = datetime.utcnow()
        # Note: Transaction commit is handled by service layer
        
        return project
    
    def get_count_by_firm(self, firm_id: int) -> int:
        """Get total count of projects for a firm"""
        return self.count(firm_id=firm_id)
    
    def get_recent_projects(self, firm_id: int, limit: int = 10) -> List[Project]:
        """Get most recent projects for a firm"""
        return Project.query.filter(
            Project.firm_id == firm_id
        ).order_by(Project.created_at.desc()).limit(limit).all()
    
    def get_projects_by_firm(self, firm_id: int, filters: Optional[Dict[str, Any]] = None, 
                            limit: Optional[int] = None) -> List[Project]:
        """Get projects for a firm with optional filters and limit"""
        query = Project.query.filter(Project.firm_id == firm_id)
        
        if filters:
            # Apply status filter if provided
            if 'status' in filters and filters['status']:
                query = query.filter(Project.status == filters['status'])
        
        query = query.order_by(Project.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_projects_by_firm_paginated(self, firm_id: int, page: int = 1, per_page: int = 50,
                                      filters: Optional[Dict[str, Any]] = None) -> PaginationResult:
        """Get projects for a firm with optional filters and pagination"""
        query = Project.query.filter(Project.firm_id == firm_id)
        
        if filters:
            # Apply status filter if provided
            if 'status' in filters and filters['status']:
                query = query.filter(Project.status == filters['status'])
        
        query = query.order_by(Project.created_at.desc())
        
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
    
    def update_progress(self, project_id: int, firm_id: int, progress_percentage: int) -> Optional[Project]:
        """Update project progress percentage"""
        project = self.get_by_id_and_firm(project_id, firm_id)
        if not project:
            return None
        
        project.progress_percentage = max(0, min(100, progress_percentage))
        project.updated_at = datetime.utcnow()
        # Note: Transaction commit is handled by service layer
        
        return project
    
    def search_projects(self, firm_id: int, query_text: str, limit: int = 20):
        """Search projects by name and description"""
        search_pattern = f'%{query_text}%'
        
        query = db.session.query(Project).filter(
            Project.firm_id == firm_id,
            or_(
                Project.name.ilike(search_pattern),
                Project.description.ilike(search_pattern)
            )
        ).order_by(Project.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
