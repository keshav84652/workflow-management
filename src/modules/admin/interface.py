"""
Admin module interfaces
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IAdminService(ABC):
    """Interface for admin service operations"""
    
    @abstractmethod
    def authenticate_admin(self, password: str) -> Dict[str, Any]:
        """Authenticate admin user with password"""
        pass
    
    @abstractmethod
    def is_admin_authenticated(self) -> bool:
        """Check if current session has admin privileges"""
        pass
    
    @abstractmethod
    def set_admin_session(self) -> None:
        """Set admin authentication in session"""
        pass
    
    @abstractmethod
    def clear_admin_session(self) -> None:
        """Clear admin authentication from session"""
        pass
    
    @abstractmethod
    def get_all_firms(self) -> List[Any]:
        """Get all firms in the system"""
        pass
    
    @abstractmethod
    def get_firm_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        pass
    
    @abstractmethod
    def generate_firm_access_code(self, firm_name: str) -> Dict[str, Any]:
        """Generate a new access code for a firm"""
        pass
    
    @abstractmethod
    def toggle_firm_status(self, firm_id: int) -> Dict[str, Any]:
        """Toggle a firm's active status"""
        pass
    
    @abstractmethod
    def get_work_types_for_firm(self, firm_id: int) -> Dict[str, Any]:
        """Get all work types for a firm"""
        pass
    
    @abstractmethod
    def create_work_type(self, name: str, description: str, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Create a new work type"""
        pass
    
    @abstractmethod
    def update_work_type(self, work_type_id: int, name: str, description: str, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Update an existing work type"""
        pass
    
    @abstractmethod
    def create_task_status(self, work_type_id: int, name: str, color: str, firm_id: int) -> Dict[str, Any]:
        """Create a new task status for a work type"""
        pass
    
    @abstractmethod
    def update_task_status(self, status_id: int, name: str, color: str, position: int, 
                          is_default: bool, is_terminal: bool, firm_id: int) -> Dict[str, Any]:
        """Update an existing task status"""
        pass

class ITemplateService(ABC):
    """Interface for template service operations"""
    
    @abstractmethod
    def create_template(self, template_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create a new template"""
        pass
    
    @abstractmethod
    def update_template(self, template_id: int, template_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Update an existing template"""
        pass
    
    @abstractmethod
    def delete_template(self, template_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a template"""
        pass
    
    @abstractmethod
    def get_templates_for_firm(self, firm_id: int) -> Dict[str, Any]:
        """Get all templates for a firm"""
        pass
    
    @abstractmethod
    def get_template_by_id(self, template_id: int, firm_id: int) -> Dict[str, Any]:
        """Get a specific template by ID"""
        pass

class IUserService(ABC):
    """Interface for user management service operations"""
    
    @abstractmethod
    def get_users_for_firm(self, firm_id: int) -> Dict[str, Any]:
        """Get all users for a firm"""
        pass
    
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any], creator_id: int) -> Dict[str, Any]:
        """Create a new user"""
        pass
    
    @abstractmethod
    def update_user(self, user_id: int, user_data: Dict[str, Any], firm_id: int) -> Dict[str, Any]:
        """Update an existing user"""
        pass
    
    @abstractmethod
    def deactivate_user(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """Deactivate a user"""
        pass
    
    @abstractmethod
    def reactivate_user(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """Reactivate a user"""
        pass
