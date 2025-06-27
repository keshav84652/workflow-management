"""
Firm Repository for CPA WorkflowPilot
Provides data access layer for firm-related operations.
"""

from typing import List, Optional
from core.db_import import db
from models import Firm
from .base import CachedRepository


class FirmRepository(CachedRepository[Firm]):
    """Repository for Firm entity with caching support"""

    def __init__(self):
        super().__init__(Firm, cache_ttl=600)  # 10 minute cache

    def get_by_id(self, firm_id: int) -> Optional[Firm]:
        """Get firm by ID"""
        return Firm.query.filter(Firm.id == firm_id).first()

    def get_all(self) -> List[Firm]:
        """Get all firms"""
        return Firm.query.order_by(Firm.name.asc()).all()

    def create(self, name: str, **kwargs) -> Firm:
        """Create a new firm"""
        firm = Firm(name=name, **kwargs)
        db.session.add(firm)
        db.session.commit()
        self._invalidate_cache(firm.id)
        return firm

    def update(self, firm_id: int, **kwargs) -> Optional[Firm]:
        """Update an existing firm"""
        firm = self.get_by_id(firm_id)
        if not firm:
            return None
        for key, value in kwargs.items():
            if hasattr(firm, key):
                setattr(firm, key, value)
        db.session.commit()
        self._invalidate_cache(firm_id)
        return firm