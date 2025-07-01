"""
Project Module Public Interface

This interface defines the public API for the project module.
Other modules MUST only interact with the project module through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IProjectService(ABC):
    """Public interface for project management operations"""
    
    @abstractmethod
    def get_project_by_id(self, project_id: int, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project by ID with firm access check
        
        Args:
            project_id: Project ID
            firm_id: Firm ID for access control
            
        Returns:
            Project data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_projects_for_firm(self, firm_id: int, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all projects for a firm
        
        Args:
            firm_id: Firm ID
            include_inactive: Whether to include inactive projects
            
        Returns:
            List of project data dictionaries
        """
        pass
    
    @abstractmethod
    def create_project(self, project_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            project_data: Project information
            firm_id: Firm ID
            user_id: User ID for audit trail
            
        Returns:
            Result dictionary with success status and project data
        """
        pass
    
    @abstractmethod
    def update_project(self, project_id: int, project_data: Dict[str, Any], firm_id: int) -> Dict[str, Any]:
        """
        Update an existing project
        
        Args:
            project_id: Project ID
            project_data: Updated project information
            firm_id: Firm ID for access control
            
        Returns:
            Result dictionary with success status
        """
        pass
    
    @abstractmethod
    def get_project_statistics(self, firm_id: int) -> Dict[str, Any]:
        """
        Get project statistics for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Statistics dictionary
        """
        pass
    
    @abstractmethod
    def get_recent_projects(self, firm_id: int, limit: int = 5) -> Dict[str, Any]:
        """
        Get recent projects for dashboard
        
        Args:
            firm_id: Firm ID
            limit: Maximum number of projects
            
        Returns:
            Recent projects dictionary
        """
        pass
    
    @abstractmethod
    def search_projects(self, firm_id: int, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search projects by name or other criteria
        
        Args:
            firm_id: Firm ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        pass


class ITaskService(ABC):
    """Public interface for task management operations"""
    
    @abstractmethod
    def get_task_by_id(self, task_id: int, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get task by ID with firm access check
        
        Args:
            task_id: Task ID
            firm_id: Firm ID for access control
            
        Returns:
            Task data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_tasks_for_project(self, project_id: int, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get all tasks for a project
        
        Args:
            project_id: Project ID
            firm_id: Firm ID for access control
            
        Returns:
            List of task data dictionaries
        """
        pass
    
    @abstractmethod
    def get_task_statistics(self, firm_id: int) -> Dict[str, Any]:
        """
        Get task statistics for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Statistics dictionary
        """
        pass
    
    @abstractmethod
    def get_recent_tasks(self, firm_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent tasks for dashboard
        
        Args:
            firm_id: Firm ID
            limit: Maximum number of tasks
            
        Returns:
            Recent tasks dictionary
        """
        pass
    
    @abstractmethod
    def get_tasks_for_dashboard(self, firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get filtered tasks for dashboard display
        
        Args:
            firm_id: Firm ID
            user_id: User ID for filtering
            
        Returns:
            Filtered tasks dictionary
        """
        pass
    
    @abstractmethod
    def get_tasks_for_calendar(self, firm_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Get tasks for calendar view
        
        Args:
            firm_id: Firm ID
            year: Calendar year
            month: Calendar month
            
        Returns:
            Calendar tasks dictionary
        """
        pass
    
    @abstractmethod
    def search_tasks(self, firm_id: int, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search tasks by title or other criteria
        
        Args:
            firm_id: Firm ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        pass