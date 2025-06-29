"""
Document Repository

Handles all database operations for document analysis results.
This extracts the persistence logic from the AIService God Object.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.db_import import db
from models import ClientDocument, DocumentChecklist, Client

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