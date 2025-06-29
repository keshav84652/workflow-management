"""
Client Repository for CPA WorkflowPilot
Provides data access layer for client-related operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_

from core.db_import import db
from src.models import Client
from repositories.base import CachedRepository, PaginationResult


class ClientRepository(CachedRepository[Client]):
    """Repository for Client entity with caching support"""
    
    def __init__(self):
        super().__init__(Client, cache_ttl=600)  # 10 minute cache
    
    def get_by_firm(self, firm_id: int, include_inactive: bool = False, limit: Optional[int] = None) -> List[Client]:
        """Get all clients for a firm with optional limit"""
        query = Client.query.filter(Client.firm_id == firm_id)
        
        if not include_inactive:
            query = query.filter(Client.is_active == True)
        
        query = query.order_by(Client.name.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_by_firm_paginated(self, firm_id: int, page: int = 1, per_page: int = 50, 
                             include_inactive: bool = False) -> PaginationResult:
        """Get clients for a firm with pagination"""
        query = Client.query.filter(Client.firm_id == firm_id)
        
        if not include_inactive:
            query = query.filter(Client.is_active == True)
        
        query = query.order_by(Client.name.asc())
        
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
    
    def search_by_name(self, firm_id: int, search_term: str, limit: Optional[int] = 100) -> List[Client]:
        """Search clients by name with optional limit"""
        query = Client.query.filter(
            Client.firm_id == firm_id,
            Client.name.ilike(f'%{search_term}%'),
            Client.is_active == True
        ).order_by(Client.name.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def search_by_name_paginated(self, firm_id: int, search_term: str, page: int = 1, 
                                per_page: int = 50) -> PaginationResult:
        """Search clients by name with pagination"""
        query = Client.query.filter(
            Client.firm_id == firm_id,
            Client.name.ilike(f'%{search_term}%'),
            Client.is_active == True
        ).order_by(Client.name.asc())
        
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
    
    def get_client_statistics(self, firm_id: int) -> Dict[str, int]:
        """Get client statistics"""
        total = self.count(firm_id=firm_id)
        active = self.count(firm_id=firm_id, is_active=True)
        inactive = total - active
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive
        }
    
    def get_by_id_and_firm(self, client_id: int, firm_id: int) -> Optional[Client]:
        """Get client by ID ensuring it belongs to the firm"""
        return Client.query.filter(
            Client.id == client_id,
            Client.firm_id == firm_id
        ).first()
    
    def get_active_count(self, firm_id: int) -> int:
        """Get count of active clients for a firm"""
        return self.count(firm_id=firm_id, is_active=True)
    
    def update_client_status(self, client_id: int, firm_id: int, is_active: bool) -> Optional[Client]:
        """Update client active status"""
        client = self.get_by_id_and_firm(client_id, firm_id)
        if not client:
            return None
        
        client.is_active = is_active
        # Note: Transaction commit is handled by service layer
        
        return client
