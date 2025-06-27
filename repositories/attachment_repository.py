"""
Attachment Repository for CPA WorkflowPilot
Provides data access layer for attachment-related operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_

from core.db_import import db
from models.documents import Attachment
from .base import CachedRepository


class AttachmentRepository(CachedRepository[Attachment]):
    """Repository for Attachment entity with caching support"""
    
    def __init__(self):
        super().__init__(Attachment, cache_ttl=300)  # 5 minute cache
    
    def get_by_firm(self, firm_id: int) -> List[Attachment]:
        """Get all attachments for a firm"""
        return Attachment.query.filter_by(firm_id=firm_id).order_by(Attachment.uploaded_at.desc()).all()
    
    def get_by_id_and_firm(self, attachment_id: int, firm_id: int) -> Optional[Attachment]:
        """Get attachment by ID ensuring it belongs to the firm"""
        return Attachment.query.filter_by(
            id=attachment_id,
            firm_id=firm_id
        ).first()
    
    def get_by_task(self, task_id: int, firm_id: int = None) -> List[Attachment]:
        """Get all attachments for a task"""
        query = Attachment.query.filter_by(task_id=task_id)
        if firm_id:
            query = query.filter_by(firm_id=firm_id)
        return query.order_by(Attachment.uploaded_at.desc()).all()
    
    def get_by_project(self, project_id: int, firm_id: int = None) -> List[Attachment]:
        """Get all attachments for a project"""
        query = Attachment.query.filter_by(project_id=project_id)
        if firm_id:
            query = query.filter_by(firm_id=firm_id)
        return query.order_by(Attachment.uploaded_at.desc()).all()
    
    def get_attachment_statistics(self, firm_id: int) -> Dict[str, Any]:
        """Get attachment statistics for a firm"""
        total = self.count_by_firm(firm_id)
        
        # Get file type distribution
        file_types = db.session.query(
            Attachment.mime_type,
            db.func.count(Attachment.id).label('count')
        ).filter_by(firm_id=firm_id).group_by(Attachment.mime_type).all()
        
        return {
            'total': total,
            'file_types': {ft.mime_type or 'unknown': ft.count for ft in file_types}
        }
    
    def count_by_firm(self, firm_id: int) -> int:
        """Count attachments for a firm"""
        return Attachment.query.filter_by(firm_id=firm_id).count()
    
    def delete_attachment(self, attachment_id: int, firm_id: int) -> bool:
        """Delete an attachment with firm verification"""
        attachment = self.get_by_id_and_firm(attachment_id, firm_id)
        if not attachment:
            return False
        
        db.session.delete(attachment)
        # Note: Transaction commit is handled by service layer
        return True
