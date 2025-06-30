"""
Document module interfaces
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from flask import Request

class IDocumentService(ABC):
    """Interface for document service operations"""
    
    @abstractmethod
    def create_checklist(self, checklist_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create a new document checklist"""
        pass
    
    @abstractmethod
    def update_checklist(self, checklist_id: int, checklist_data: Dict[str, Any], firm_id: int) -> Dict[str, Any]:
        """Update an existing checklist"""
        pass
    
    @abstractmethod
    def delete_checklist(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Delete a checklist"""
        pass
    
    @abstractmethod
    def get_checklists_for_firm(self, firm_id: int) -> Dict[str, Any]:
        """Get all checklists for a firm"""
        pass
    
    @abstractmethod
    def get_checklist_by_id(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Get a specific checklist by ID"""
        pass
    
    @abstractmethod
    def get_checklist_by_token(self, token: str) -> Dict[str, Any]:
        """Get a checklist by public access token"""
        pass
    
    @abstractmethod
    def share_checklist(self, checklist_id: int, firm_id: int, expiration_days: Optional[int] = None) -> Dict[str, Any]:
        """Generate public access link for a checklist"""
        pass
    
    @abstractmethod
    def revoke_checklist_access(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Revoke public access to a checklist"""
        pass
    
    @abstractmethod
    def update_checklist_item_status(self, item_id: int, status: str, checklist_token: str) -> Dict[str, Any]:
        """Update the status of a checklist item"""
        pass
    
    @abstractmethod
    def upload_client_document(self, request: Request, checklist_token: str, item_id: Optional[int] = None) -> Dict[str, Any]:
        """Handle client document upload"""
        pass

class IAIService(ABC):
    """Interface for AI analysis service operations"""
    
    @abstractmethod
    def analyze_documents(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Analyze documents in a checklist using AI"""
        pass
    
    @abstractmethod
    def get_analysis_results(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Get AI analysis results for a checklist"""
        pass
    
    @abstractmethod
    def generate_income_worksheet(self, checklist_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Generate income worksheet from analyzed documents"""
        pass
    
    @abstractmethod
    def validate_document_completeness(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Validate if all required documents are uploaded and analyzed"""
        pass
