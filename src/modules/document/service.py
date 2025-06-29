"""
DocumentService: Handles all business logic for documents and checklists, including sharing.
Updated to use proper service patterns and repositories.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import secrets

from src.shared.database.db_import import db
from src.models import DocumentChecklist, Client, ChecklistItem, ClientDocument, IncomeWorksheet
from src.shared.base import BaseService, transactional
from src.modules.client.repository import ClientRepository


class DocumentService(BaseService):
    def __init__(self):
        super().__init__()
        self.client_repository = ClientRepository()
    @staticmethod
    def update_checklist_item_status(token, item_id, new_status):
        """Update checklist item status via public token"""
        try:
            # Find checklist by token
            checklist = DocumentChecklist.query.filter_by(
                public_access_token=token,
                public_access_enabled=True
            ).first()
            
            if not checklist:
                return {'success': False, 'message': 'Invalid or expired access token'}
            
            # Validate status
            if new_status not in ['already_provided', 'not_applicable', 'pending']:
                return {'success': False, 'message': 'Invalid status selected'}
            
            item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first()
            if not item:
                return {'success': False, 'message': 'Checklist item not found'}
            
            # If changing from uploaded status, remove the uploaded file
            if item.status == 'uploaded' and new_status != 'uploaded':
                existing_doc = ClientDocument.query.filter_by(
                    client_id=checklist.client_id,
                    checklist_item_id=item_id
                ).first()
                
                if existing_doc:
                    # Remove file
                    import os
                    if os.path.exists(existing_doc.file_path):
                        os.remove(existing_doc.file_path)
                    db.session.delete(existing_doc)
            
            # Update status
            item.status = new_status
            item.updated_at = datetime.utcnow()
            
            db.session.commit()
            
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
            db.session.rollback()
            return {'success': False, 'message': f'Error updating status: {str(e)}'}
    
    def generate_share_token(self, checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        if not checklist.public_access_token:
            checklist.public_access_token = secrets.token_urlsafe(32)
            checklist.public_access_enabled = True
            db.session.commit()
        return checklist

    @staticmethod  
    def revoke_share(checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        checklist.public_access_enabled = False
        db.session.commit()
        return checklist

    @staticmethod
    def regenerate_share_token(checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        checklist.public_access_token = secrets.token_urlsafe(32)
        checklist.public_access_enabled = True
        db.session.commit()
        return checklist
    
    @staticmethod
    def create_checklist(name, description=None, client_id=None, firm_id=None, user_id=None):
        """Create a new document checklist"""
        try:
            if not name or not name.strip():
                return {'success': False, 'error': 'Checklist name is required'}
            
            checklist = DocumentChecklist(
                name=name.strip(),
                description=description,
                client_id=client_id,
                created_by=user_id
            )
            
            db.session.add(checklist)
            db.session.commit()
            
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
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def add_checklist_item(checklist_id, name, description=None, firm_id=None, user_id=None):
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
            db.session.commit()
            
            return {
                'success': True,
                'item_id': item.id,
                'message': 'Checklist item added successfully'
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def upload_file_to_checklist_item(item_id, file_path, original_filename, firm_id=None, user_id=None):
        """Upload file to checklist item"""
        try:
            item = ChecklistItem.query.get(item_id)
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
            db.session.commit()
            
            return {
                'success': True,
                'message': 'File uploaded successfully'
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_checklists_for_firm(self, firm_id):
        """Get all checklists for a firm"""
        return DocumentChecklist.query.join(Client).filter(
            Client.firm_id == firm_id
        ).order_by(DocumentChecklist.created_at.desc()).all()
    
    def get_clients_for_firm(self, firm_id):
        """Get all clients for a firm - used by document blueprints"""
        return self.client_repository.get_by_firm(firm_id)
    
    def get_uploaded_documents(self, firm_id):
        """Get all uploaded documents for a firm"""
        from src.models import ClientDocument, ChecklistItem, DocumentChecklist, Client
        return ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            Client.firm_id == firm_id
        ).order_by(ClientDocument.uploaded_at.desc()).all()
    
    def get_document_for_download(self, document_id, firm_id):
        """Get document for download with firm access check"""
        from src.models import ClientDocument, ChecklistItem, DocumentChecklist, Client
        return ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
    
    def get_client_by_id_and_firm(self, client_id, firm_id):
        """Get client by ID with firm access check"""
        from src.models import Client
        return Client.query.filter_by(id=client_id, firm_id=firm_id).first()
    
    def get_checklists_by_client_and_firm(self, client_id, firm_id):
        """Get checklists for specific client and firm"""
        return DocumentChecklist.query.filter_by(
            client_id=client_id,
            firm_id=firm_id
        ).all()
    
    def get_checklist_by_token(self, token):
        """Get checklist by public access token"""
        return DocumentChecklist.query.filter_by(
            public_access_token=token,
            public_access_enabled=True
        ).first()
    
    def get_active_checklists_with_client_filter(self, firm_id):
        """Get active checklists with client join for firm"""
        return DocumentChecklist.query.join(Client).filter(
            Client.firm_id == firm_id,
            DocumentChecklist.is_active == True
        ).order_by(DocumentChecklist.created_at.desc()).all()
    
    @classmethod
    def get_checklist_by_id(cls, checklist_id, firm_id):
        """Get checklist by ID with firm access check"""
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
    
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
    
    @staticmethod
    def perform_checklist_ai_analysis(checklist):
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
                
                try:
                    # Save checklist analysis with proper error handling
                    checklist.ai_analysis_completed = True
                    checklist.ai_analysis_results = json.dumps(checklist_summary)
                    checklist.ai_analysis_timestamp = datetime.utcnow()
                    
                    db.session.commit()
                    
                except Exception as db_error:
                    print(f"Database error saving checklist analysis: {db_error}")
                    db.session.rollback()
            
        except Exception as e:
            print(f"Error performing checklist AI analysis: {e}")
            try:
                db.session.rollback()
            except:
                pass
