"""
DocumentService: Handles all business logic for documents and checklists, including sharing.
Updated to use proper service patterns and repositories.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import secrets

from src.shared.database.db_import import db
from .models import DocumentChecklist, ChecklistItem, ClientDocument, IncomeWorksheet
from src.shared.base import BaseService, transactional
from src.shared.di_container import get_service
from src.modules.client.interface import IClientService
from .repository import DocumentRepository


class DocumentService(BaseService):
    def __init__(self):
        super().__init__()
        # Use dependency injection to get client service
        try:
            self.client_service = get_service(IClientService)
        except ValueError:
            # Fallback to direct instantiation if DI not set up
            from src.modules.client.service import ClientService
            self.client_service = ClientService()
        self.document_repository = DocumentRepository()
    @transactional
    def update_checklist_item_status(self, token, item_id, new_status):
        """Update checklist item status via public token"""
        try:
            # Find checklist by token
            checklist = self.document_repository.get_checklist_by_token(token)
            
            if not checklist:
                return {'success': False, 'message': 'Invalid or expired access token'}
            
            # Validate status
            if new_status not in ['already_provided', 'not_applicable', 'pending']:
                return {'success': False, 'message': 'Invalid status selected'}
            
            item = self.document_repository.get_checklist_item_by_id(item_id, checklist.id)
            if not item:
                return {'success': False, 'message': 'Checklist item not found'}
            
            # If changing from uploaded status, remove the uploaded file
            if item.status == 'uploaded' and new_status != 'uploaded':
                existing_doc = self.document_repository.get_client_document_by_item(
                    checklist.client_id,
                    item_id
                )
                
                if existing_doc:
                    # Remove file
                    import os
                    if os.path.exists(existing_doc.file_path):
                        os.remove(existing_doc.file_path)
                    db.session.delete(existing_doc)
            
            # Update status
            item.status = new_status
            item.updated_at = datetime.utcnow()
            
            status_messages = {
                'already_provided': 'Marked as already provided',
                'not_applicable': 'Marked as not applicable',
                'pending': 'Reset to pending'
            }
            
            return {
                'success': True,
                'message': status_messages.get(new_status, 'Status updated')
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @transactional
    def generate_share_token(self, checklist_id, firm_id):
        checklist = self.document_repository.get_checklist_by_id_with_firm_access(
            checklist_id, firm_id
        )
        if not checklist:
            raise ValueError(f"Checklist {checklist_id} not found")
        if not checklist.public_access_token:
            checklist.public_access_token = secrets.token_urlsafe(32)
            checklist.public_access_enabled = True
        return checklist

    @transactional
    def revoke_share(self, checklist_id, firm_id):
        checklist = self.document_repository.get_checklist_by_id_with_firm_access(
            checklist_id, firm_id
        )
        if not checklist:
            raise ValueError(f"Checklist {checklist_id} not found")
        checklist.public_access_enabled = False
        return checklist

    @transactional
    def regenerate_share_token(self, checklist_id, firm_id):
        checklist = self.document_repository.get_checklist_by_id_with_firm_access(
            checklist_id, firm_id
        )
        if not checklist:
            raise ValueError(f"Checklist {checklist_id} not found")
        checklist.public_access_token = secrets.token_urlsafe(32)
        checklist.public_access_enabled = True
        return checklist
    
    @transactional
    def create_checklist(self, name, description=None, client_id=None, firm_id=None, user_id=None):
        """Create a new document checklist"""
        try:
            if not name or not name.strip():
                return {'success': False, 'message': 'Checklist name is required'}
            
            checklist = DocumentChecklist(
                name=name.strip(),
                description=description,
                client_id=client_id,
                created_by=user_id
            )
            
            db.session.add(checklist)
            
            # Publish document creation event
            from src.shared.events.schemas import DocumentCreatedEvent
            from src.shared.events.publisher import publish_event
            event = DocumentCreatedEvent(
                document_id=checklist.id,
                firm_id=firm_id or 0,
                name=checklist.name,
                status='pending'
            )
            publish_event(event)
            
            return {
                'success': True,
                'checklist_id': checklist.id,
                'message': 'Checklist created successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @transactional
    def add_checklist_item(self, checklist_id, name, description=None, firm_id=None, user_id=None):
        """Add item to checklist"""
        try:
            if not name or not name.strip():
                return {'success': False, 'error': 'Item name is required'}
            
            item = ChecklistItem(
                title=name.strip(),
                description=description,
                checklist_id=checklist_id,
                status='pending'
            )
            
            db.session.add(item)
            
            return {
                'success': True,
                'item_id': item.id,
                'message': 'Checklist item added successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @transactional
    def upload_file_to_checklist_item(self, item_id, file_path, original_filename, firm_id=None, user_id=None):
        """Upload file to checklist item"""
        try:
            item = self.document_repository.get_checklist_item_by_id_only(item_id)
            if not item:
                return {'success': False, 'error': 'Checklist item not found'}
            
            # Create document record
            document = ClientDocument(
                file_path=file_path,
                original_filename=original_filename,
                client_id=item.checklist.client_id,
                checklist_item_id=item_id,
                uploaded_by=user_id
            )
            
            db.session.add(document)
            item.status = 'uploaded'
            
            return {
                'success': True,
                'message': 'File uploaded successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_checklists_for_firm(self, firm_id):
        """Get all checklists for a firm"""
        return self.document_repository.get_checklists_for_firm(firm_id)
    
    def get_clients_for_firm(self, firm_id):
        """Get all clients for a firm - delegated to client service"""
        result = self.client_service.get_clients_for_api(firm_id)
        return result.get('clients', []) if result.get('success') else []
    
    def get_uploaded_documents(self, firm_id):
        """Get all uploaded documents for a firm"""
        return self.document_repository.get_uploaded_documents_for_firm(firm_id)
    
    def get_document_for_download(self, document_id, firm_id):
        """Get document for download with firm access check"""
        return self.document_repository.get_document_for_download(document_id, firm_id)
    
    def get_client_by_id_and_firm(self, client_id, firm_id):
        """Get client by ID with firm access check - delegated to client service"""
        return self.client_service.get_client_by_id(client_id, firm_id)
    
    def get_checklists_by_client_and_firm(self, client_id, firm_id):
        """Get checklists for specific client and firm"""
        return self.document_repository.get_checklists_by_client_and_firm(client_id, firm_id)
    
    def get_checklist_by_token(self, token):
        """Get checklist by public access token"""
        return self.document_repository.get_checklist_by_token(token)
    
    def get_active_checklists_with_client_filter(self, firm_id):
        """Get active checklists with client join for firm"""
        return self.document_repository.get_active_checklists_with_client_filter(firm_id)
    
    def get_checklist_by_id(self, checklist_id, firm_id):
        """Get checklist by ID with firm access check"""
        return self.document_repository.get_checklist_by_id_with_firm_check(checklist_id, firm_id)
    
    def get_document_filename_by_id(self, document_id):
        """Get document filename by ID"""
        try:
            document = ClientDocument.query.get(document_id)
            return document.original_filename if document else f'document_{document_id}'
        except:
            return f'document_{document_id}'
    
    def get_income_worksheet_by_id_with_access_check(self, worksheet_id, firm_id):
        """Get income worksheet by ID with firm access check"""
        from src.models import IncomeWorksheet
        worksheet = IncomeWorksheet.query.get(worksheet_id)
        if not worksheet:
            return None
        
        # Check firm access through checklist -> client -> firm
        checklist = worksheet.checklist
        if checklist and checklist.client and checklist.client.firm_id == firm_id:
            return worksheet
        return None
    
    def get_worksheet_data_for_download(self, worksheet_id, firm_id):
        """Get worksheet data for download without exposing model to blueprint"""
        import json
        
        worksheet = self.get_income_worksheet_by_id_with_access_check(worksheet_id, firm_id)
        if not worksheet:
            return {
                'success': False,
                'message': 'Worksheet not found or access denied'
            }
        
        try:
            worksheet_data = json.loads(worksheet.worksheet_data)
            return {
                'success': True,
                'data': worksheet_data,
                'worksheet_id': worksheet_id
            }
        except (json.JSONDecodeError, AttributeError) as e:
            return {
                'success': False,
                'message': f'Error parsing worksheet data: {str(e)}'
            }
    
    @transactional
    def perform_checklist_ai_analysis(self, checklist):
        """Perform one-time AI analysis for a checklist and all its documents"""
        if checklist.ai_analysis_completed:
            return
        
        try:
            import json
            from datetime import datetime
            
            # Analyze all uploaded documents that haven't been analyzed yet
            total_documents = 0
            analyzed_documents = 0
            document_types = {}
            confidence_scores = []
            
            for item in checklist.items:
                for document in item.client_documents:
                    total_documents += 1
                    if not document.ai_analysis_completed:
                        # Skip analysis in this function - let individual requests handle it
                        # to avoid database locking issues
                        pass
                    else:
                        # Document already analyzed
                        analyzed_documents += 1
                        if document.ai_document_type:
                            document_types[document.ai_document_type] = document_types.get(document.ai_document_type, 0) + 1
                        if document.ai_confidence_score:
                            confidence_scores.append(document.ai_confidence_score)
            
            # Only save checklist summary if we have some analyzed documents
            if analyzed_documents > 0:
                # Create checklist-level summary
                checklist_summary = {
                    'total_documents': total_documents,
                    'analyzed_documents': analyzed_documents,
                    'document_types': document_types,
                    'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'status': 'completed' if analyzed_documents == total_documents else 'partial'
                }
                
                # Save checklist analysis
                checklist.ai_analysis_completed = True
                checklist.ai_analysis_results = json.dumps(checklist_summary)
                checklist.ai_analysis_timestamp = datetime.utcnow()
                
        except Exception as e:
            print(f"Error in checklist AI analysis: {e}")
