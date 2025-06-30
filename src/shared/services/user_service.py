"""
Shared User Service for CPA WorkflowPilot
Provides user-related functionality that can be used across modules without creating circular dependencies.
"""

import logging
from typing import List, Dict, Any
from src.shared.base import BaseService
from src.shared.di_container import get_service
from src.modules.auth.interface import IAuthService

logger = logging.getLogger(__name__)


class SharedUserService(BaseService):
    """Shared service for user operations to avoid circular dependencies"""
    
    def __init__(self):
        super().__init__()
        # Use dependency injection to get auth service
        try:
            self.auth_service = get_service(IAuthService)
        except ValueError:
            # Fallback to direct instantiation if DI not set up
            from src.modules.auth.service import AuthService
            self.auth_service = AuthService()
    
    def get_users_by_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get all users for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of user dictionaries
        """
        try:
            return self.auth_service.get_users_for_firm(firm_id)
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
            if firm_id is not None:
                return self.auth_service.get_user_by_id(user_id, firm_id)
            else:
                # For cases where firm validation is not needed, we still need firm_id
                # This is a limitation of the interface - we could enhance it later
                logger.warning(f"get_user_by_id called without firm_id for user {user_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting user {user_id} for firm {firm_id}: {e}")
        return None