"""
User Repository for CPA WorkflowPilot
Provides data access layer for user-related operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_

from core.db_import import db
from models import User
from .base import CachedRepository


class UserRepository(CachedRepository[User]):
    """Repository for User entity with caching support"""
    
    def __init__(self):
        super().__init__(User, cache_ttl=600)  # 10 minute cache
    
    def get_by_firm(self, firm_id: int, include_inactive: bool = False) -> List[User]:
        """Get all users for a firm"""
        query = User.query.filter(User.firm_id == firm_id)
        
        # Note: is_active field doesn't exist in current schema, so we return all users
        # TODO: Add is_active field to User model and database schema when ready
        
        return query.order_by(User.name.asc()).all()
    
    def search_by_name(self, firm_id: int, search_term: str) -> List[User]:
        """Search users by name"""
        return User.query.filter(
            User.firm_id == firm_id,
            User.name.ilike(f'%{search_term}%')
        ).order_by(User.name.asc()).all()
    
    def get_user_statistics(self, firm_id: int) -> Dict[str, int]:
        """Get user statistics"""
        total = self.count(firm_id=firm_id)
        # TODO: Implement active/inactive when is_active field is added
        active = total  # All users considered active for now
        inactive = 0
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive
        }
    
    def get_count_by_firm(self, firm_id: int) -> int:
        """Get total count of users for a firm"""
        return self.count(firm_id=firm_id)
    
    def get_by_id_and_firm(self, user_id: int, firm_id: int) -> Optional[User]:
        """Get user by ID ensuring it belongs to the firm"""
        return User.query.filter(
            User.id == user_id,
            User.firm_id == firm_id
        ).first()
    
    def get_users_by_firm(self, firm_id: int, include_inactive: bool = False) -> List[User]:
        """Alias for get_by_firm to maintain compatibility"""
        return self.get_by_firm(firm_id, include_inactive)
