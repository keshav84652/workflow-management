"""
Shared User Service for CPA WorkflowPilot
Provides user-related functionality that can be used across modules without creating circular dependencies.
"""

import logging
from typing import List, Dict, Any
from src.shared.base import BaseService
from src.modules.auth.repository import UserRepository

logger = logging.getLogger(__name__)


class SharedUserService(BaseService):
    """Shared service for user operations to avoid circular dependencies"""
    
    def __init__(self):
        super().__init__()
        self.user_repository = UserRepository()
    
    def get_users_by_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get all users for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of user dictionaries
        """
        try:
            users = self.user_repository.get_users_by_firm(firm_id)
            return [{
                'id': user.id,
                'name': user.name,
                'role': user.role,
                'firm_id': user.firm_id
            } for user in users]
        except Exception as e:
            logger.error(f"Error getting users for firm {firm_id}: {e}")
            return []
    
    def get_user_by_id(self, user_id: int, firm_id: int = None) -> Dict[str, Any]:
        """
        Get user by ID with optional firm validation
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID for validation
            
        Returns:
            User dictionary or None
        """
        try:
            user = self.user_repository.get_by_id(user_id)
            if user and (firm_id is None or user.firm_id == firm_id):
                return {
                    'id': user.id,
                    'name': user.name,
                    'role': user.role,
                    'firm_id': user.firm_id
                }
        except Exception as e:
            logger.error(f"Error getting user {user_id} for firm {firm_id}: {e}")
        return None