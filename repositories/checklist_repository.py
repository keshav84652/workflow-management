"""
Checklist Repository for CPA WorkflowPilot
Provides data access layer for checklist-related operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_
from datetime import datetime

from core.db_import import db
from models.documents import DocumentChecklist, ChecklistItem, ClientDocument
from models.clients import Client
from .base import CachedRepository


class ChecklistRepository(CachedRepository[DocumentChecklist]):
    """Repository for DocumentChecklist entity with caching support"""
    
    def __init__(self):
        super().__init__(DocumentChecklist, cache_ttl=600)  # 10 minute cache
    
    def get_by_firm(self, firm_id: int, include_inactive: bool = False) -> List[DocumentChecklist]:
        """Get all checklists for a firm"""
        query = DocumentChecklist.query.join(Client).filter(Client.firm_id == firm_id)
        
        if not include_inactive:
            query = query.filter(DocumentChecklist.is_active == True)
        
        return query.order_by(DocumentChecklist.created_at.desc()).all()
    
    def get_by_id_and_firm(self, checklist_id: int, firm_id: int) -> Optional[DocumentChecklist]:
        """Get checklist by ID ensuring it belongs to the firm"""
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
    
    def get_by_client(self, client_id: int, firm_id: int) -> List[DocumentChecklist]:
        """Get all checklists for a client"""
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.client_id == client_id,
            Client.firm_id == firm_id,
            DocumentChecklist.is_active == True
        ).order_by(DocumentChecklist.created_at.desc()).all()
    
    def get_by_access_token(self, access_token: str) -> Optional[DocumentChecklist]:
        """Get checklist by access token for public access"""
        return DocumentChecklist.query.filter_by(
            access_token=access_token,
            is_active=True
        ).first()
    
    def get_checklist_statistics(self, firm_id: int) -> Dict[str, Any]:
        """Get checklist statistics for a firm"""
        total = self.count_by_firm(firm_id)
        active = self.count_by_firm(firm_id, is_active=True)
        inactive = total - active
        
        # Count checklists needing AI analysis
        needs_analysis = DocumentChecklist.query.join(Client).filter(
            Client.firm_id == firm_id,
            DocumentChecklist.ai_analysis_completed == False
        ).count()
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'needs_ai_analysis': needs_analysis
        }
    
    def count_by_firm(self, firm_id: int, is_active: bool = None) -> int:
        """Count checklists for a firm"""
        query = DocumentChecklist.query.join(Client).filter(Client.firm_id == firm_id)
        
        if is_active is not None:
            query = query.filter(DocumentChecklist.is_active == is_active)
        
        return query.count()
    
    def update_checklist_status(self, checklist_id: int, firm_id: int, is_active: bool) -> Optional[DocumentChecklist]:
        """Update checklist active status"""
        checklist = self.get_by_id_and_firm(checklist_id, firm_id)
        if not checklist:
            return None
        
        checklist.is_active = is_active
        db.session.commit()
        self._invalidate_cache(checklist_id)
        
        return checklist


class ChecklistItemRepository(CachedRepository[ChecklistItem]):
    """Repository for ChecklistItem entity with caching support"""
    
    def __init__(self):
        super().__init__(ChecklistItem, cache_ttl=300)  # 5 minute cache
    
    def get_by_checklist(self, checklist_id: int) -> List[ChecklistItem]:
        """Get all items for a checklist ordered by sort_order"""
        return ChecklistItem.query.filter_by(
            checklist_id=checklist_id
        ).order_by(ChecklistItem.sort_order).all()
    
    def get_by_id_and_checklist(self, item_id: int, checklist_id: int) -> Optional[ChecklistItem]:
        """Get item by ID ensuring it belongs to the checklist"""
        return ChecklistItem.query.filter_by(
            id=item_id,
            checklist_id=checklist_id
        ).first()
    
    def update_item_status(self, item_id: int, status: str) -> Optional[ChecklistItem]:
        """Update item status"""
        item = self.get_by_id(item_id)
        if not item:
            return None
        
        item.status = status
        item.updated_at = datetime.utcnow()
        db.session.commit()
        self._invalidate_cache(item_id)
        
        return item
    
    def get_max_sort_order(self, checklist_id: int) -> int:
        """Get maximum sort order for a checklist"""
        result = db.session.query(db.func.max(ChecklistItem.sort_order)).filter_by(
            checklist_id=checklist_id
        ).scalar()
        return result or 0
    
    def reorder_items(self, checklist_id: int, item_orders: List[Dict[str, int]]) -> bool:
        """Reorder checklist items"""
        try:
            for order_data in item_orders:
                item_id = order_data.get('item_id')
                new_order = order_data.get('sort_order')
                
                if item_id and new_order is not None:
                    item = self.get_by_id_and_checklist(item_id, checklist_id)
                    if item:
                        item.sort_order = new_order
                        self._invalidate_cache(item_id)
            
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False