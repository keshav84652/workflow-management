"""
Document Repository

Handles all database operations for documents, checklists, and analysis results.
This extracts the persistence logic from services to enforce repository pattern.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.shared.database.db_import import db
from src.models import ClientDocument, DocumentChecklist, Client, ChecklistItem
from src.shared.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentAnalysisRepository:
    """
    Repository for managing document analysis data persistence.
    
    Handles saving and retrieving AI analysis results, managing document
    metadata, and providing data access for the document analysis system.
    """
    
    def __init__(self):
        """Initialize the document analysis repository"""
        pass
    
    def save_analysis_results(self, document_id: int, results: Dict[str, Any]) -> bool:
        """
        Save analysis results to the database
        
        Args:
            document_id: Document ID
            results: Analysis results to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Find the document
            document = ClientDocument.query.get(document_id)
            if not document:
                logger.warning(f"Document {document_id} not found for saving AI results")
                return False
            
            # Save analysis data
            document.ai_analysis_results = json.dumps(results)
            document.ai_analysis_completed = True
            document.ai_analysis_timestamp = datetime.utcnow()
            
            # Extract and save summary fields
            combined = results.get('combined_analysis', {})
            document.ai_confidence_score = results.get('confidence_score', 0)
            document.ai_document_type = combined.get('document_type', 'unknown')
            
            db.session.commit()
            logger.info(f"Saved AI analysis results for document {document_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save AI analysis results for document {document_id}: {e}")
            return False
    
    def get_analysis_results(self, document_id: int, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get existing analysis results for a document
        
        Args:
            document_id: Document ID
            firm_id: Firm ID for access control
            
        Returns:
            Analysis results if found, None otherwise
        """
        try:
            # Get document with firm verification
            document = db.session.query(ClientDocument).join(Client).filter(
                ClientDocument.id == document_id,
                Client.firm_id == firm_id
            ).first()
            
            if not document:
                return None
            
            if not document.ai_analysis_completed or not document.ai_analysis_results:
                return None
            
            try:
                return json.loads(document.ai_analysis_results)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in analysis results for document {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving analysis results for document {document_id}: {e}")
            return None
    
    def get_document_with_firm_check(self, document_id: int, firm_id: int) -> Optional[ClientDocument]:
        """
        Get document with firm access verification
        
        Args:
            document_id: Document ID
            firm_id: Firm ID for access control
            
        Returns:
            Document if found and accessible, None otherwise
        """
        try:
            return db.session.query(ClientDocument).join(Client).filter(
                ClientDocument.id == document_id,
                Client.firm_id == firm_id
            ).first()
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None


class DocumentRepository(BaseRepository):
    """Repository for document and checklist data access"""
    
    def __init__(self):
        super().__init__(DocumentChecklist)
    
    def get_checklists_for_firm(self, firm_id: int) -> List[DocumentChecklist]:
        """Get all checklists for a firm"""
        return DocumentChecklist.query.join(Client).filter(
            Client.firm_id == firm_id
        ).order_by(DocumentChecklist.created_at.desc()).all()
    
    def get_checklist_by_token(self, token: str) -> Optional[DocumentChecklist]:
        """Get checklist by public access token"""
        return DocumentChecklist.query.filter_by(
            public_access_token=token,
            public_access_enabled=True
        ).first()
    
    def get_checklist_by_id_with_firm_access(self, checklist_id: int, firm_id: int) -> Optional[DocumentChecklist]:
        """Get checklist with firm access check"""
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
    
    def get_checklist_by_id_with_firm_check(self, checklist_id: int, firm_id: int) -> Optional[DocumentChecklist]:
        """Get checklist by ID with firm access check (alias for consistency)"""
        return self.get_checklist_by_id_with_firm_access(checklist_id, firm_id)
    
    def get_checklist_item_by_id(self, item_id: int, checklist_id: int) -> Optional[ChecklistItem]:
        """Get checklist item with access check"""
        return ChecklistItem.query.filter_by(
            id=item_id, 
            checklist_id=checklist_id
        ).first()
    
    def get_checklist_item_by_id_only(self, item_id: int) -> Optional[ChecklistItem]:
        """Get checklist item by ID only"""
        return ChecklistItem.query.get(item_id)
    
    def get_client_document_by_item(self, client_id: int, checklist_item_id: int) -> Optional[ClientDocument]:
        """Get document by client and checklist item"""
        return ClientDocument.query.filter_by(
            client_id=client_id,
            checklist_item_id=checklist_item_id
        ).first()
    
    def get_uploaded_documents_for_firm(self, firm_id: int) -> List[ClientDocument]:
        """Get all uploaded documents for a firm"""
        return db.session.query(ClientDocument).join(
            ChecklistItem, ClientDocument.checklist_item_id == ChecklistItem.id
        ).join(
            DocumentChecklist, ChecklistItem.checklist_id == DocumentChecklist.id
        ).join(
            Client, DocumentChecklist.client_id == Client.id
        ).filter(
            Client.firm_id == firm_id
        ).all()
    
    def get_document_for_download(self, document_id: int, firm_id: int) -> Optional[ClientDocument]:
        """Get document with firm access check for download"""
        return db.session.query(ClientDocument).join(
            ChecklistItem, ClientDocument.checklist_item_id == ChecklistItem.id
        ).join(
            DocumentChecklist, ChecklistItem.checklist_id == DocumentChecklist.id
        ).join(
            Client, DocumentChecklist.client_id == Client.id
        ).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
    
    def get_checklists_by_client_and_firm(self, client_id: int, firm_id: int) -> List[DocumentChecklist]:
        """Get checklists by client with firm access check"""
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.client_id == client_id,
            Client.firm_id == firm_id
        ).all()
    
    def get_active_checklists_with_client_filter(self, firm_id: int) -> List[Dict[str, Any]]:
        """Get active checklists with client information"""
        checklists = self.get_checklists_for_firm(firm_id)
        result = []
        for checklist in checklists:
            result.append({
                'id': checklist.id,
                'name': checklist.name,
                'client_name': checklist.client.name if checklist.client else 'No Client',
                'client_id': checklist.client_id,
                'created_at': checklist.created_at,
                'items_count': len(checklist.items) if checklist.items else 0
            })
        return result