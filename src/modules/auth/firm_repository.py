"""
Firm Repository for CPA WorkflowPilot
Provides data access layer for firm-related operations.
"""

from typing import List, Dict, Any, Optional
from src.shared.repositories import CachedRepository
from src.models import Firm


class FirmRepository(CachedRepository[Firm]):
    """Repository for Firm entity with caching support"""
    
    def __init__(self):
        super().__init__(Firm, cache_ttl=3600)  # 1 hour cache for firms
    
    def get_by_access_code(self, access_code: str, active_only: bool = True) -> Optional[Firm]:
        """Get firm by access code"""
        query = Firm.query.filter(Firm.access_code == access_code)
        
        if active_only:
            query = query.filter(Firm.is_active == True)
        
        return query.first()
    
    def get_active_firms(self) -> List[Firm]:
        """Get all active firms"""
        return Firm.query.filter(Firm.is_active == True).order_by(Firm.name.asc()).all()
    
    def get_firm_by_id(self, firm_id: int) -> Optional[Firm]:
        """Get firm by ID (cached)"""
        return self.get_by_id(firm_id)
    
    def get_firm_statistics(self) -> Dict[str, Any]:
        """Get firm statistics"""
        total_firms = self.count()
        active_firms = self.count(is_active=True)
        inactive_firms = total_firms - active_firms
        
        return {
            'total': total_firms,
            'active': active_firms,
            'inactive': inactive_firms
        }