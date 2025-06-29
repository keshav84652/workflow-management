"""
Portal service layer for client portal business logic
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
import os
import uuid
import mimetypes

from core.db_import import db
from src.models import (
    ClientUser, Client, DocumentChecklist, ChecklistItem, ClientDocument
)


class PortalService:
    """Service class for client portal-related business operations"""

    def __init__(self):
        pass
    

    def authenticate_client(self, access_code: str) -> Dict[str, Any]:
        """
        Authenticate a client user with access code
        
        Args:
            access_code: The client's access code
            
        Returns:
            Dict containing success status, client data, and any error messages
        """
        try:
            access_code = access_code.strip()
            client_user = ClientUser.query.filter_by(
                access_code=access_code, 
                is_active=True
            ).first()
            
            if not client_user:
                return {
                    'success': False,
                    'message': 'Invalid access code',
                    'client_user': None
                }
            
            # Update last login
            client_user.last_login = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Authentication successful',
                'client_user': client_user,
                'client_id': client_user.client_id,
                'client_email': client_user.email,
                'client_user_id': client_user.id
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}',
                'client_user': None
            }
    

    def get_client_dashboard_data(self, client_id: int) -> Dict[str, Any]:
        """
        Get dashboard data for a client
        
        Args:
            client_id: The client's ID
            
        Returns:
            Dict containing client and checklist data
        """
        try:
            client = Client.query.get(client_id)
            if not client:
                return {
                    'success': False,
                    'message': 'Client not found',
                    'client': None,
                    'checklists': []
                }
            
            # Get active checklists for this client
            checklists = DocumentChecklist.query.filter_by(
                client_id=client_id,
                is_active=True
            ).all()
            
            return {
                'success': True,
                'client': client,
                'checklists': checklists
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving dashboard data: {str(e)}',
                'client': None,
                'checklists': []
            }
    

    def validate_file_upload(filename: str, file_size: int = None) -> Dict[str, Any]:
        """
        Validate file upload requirements
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes (optional)
            
        Returns:
            Dict containing validation results
        """
        if not filename:
            return {
                'success': False,
                'message': 'No file selected'
            }
        
        # Check if file has extension
        if '.' not in filename:
            return {
                'success': False,
                'message': 'File must have an extension'
            }
        
        # Check file extension
        extension = filename.rsplit('.', 1)[1].lower()
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
        
        if extension not in allowed_extensions:
            return {
                'success': False,
                'message': 'File type not allowed'
            }
        
        # Check file size if provided
        if file_size is not None:
            max_size = 16 * 1024 * 1024  # 16MB
            if file_size > max_size:
                return {
                    'success': False,
                    'message': f'File size too large. Maximum {max_size // (1024*1024)}MB allowed'
                }
        
        return {
            'success': True,
            'message': 'File validation passed'
        }
    

    def verify_checklist_item_access(self, item_id: int, client_id: int) -> Dict[str, Any]:
        """
        Verify that a checklist item belongs to the client
        
        Args:
            item_id: The checklist item ID
            client_id: The client's ID
            
        Returns:
            Dict containing verification results and item data
        """
        try:
            item = ChecklistItem.query.join(DocumentChecklist).filter(
                ChecklistItem.id == item_id,
                DocumentChecklist.client_id == client_id
            ).first()
            
            if not item:
                return {
                    'success': False,
                    'message': 'Invalid document item',
                    'item': None
                }
            
            return {
                'success': True,
                'item': item
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error verifying access: {str(e)}',
                'item': None
            }
    

    def upload_client_document(file, item_id: int, client_id: int) -> Dict[str, Any]:
        """
        Handle client document upload
        
        Args:
            file: The uploaded file object
            item_id: The checklist item ID
            client_id: The client's ID
            
        Returns:
            Dict containing upload results
        """
        try:
            # Verify checklist item access
            verification = PortalService.verify_checklist_item_access(item_id, client_id)
            if not verification['success']:
                return verification
            
            item = verification['item']
            
            # Validate file
            validation = PortalService.validate_file_upload(file.filename, len(file.read()))
            file.seek(0)  # Reset file pointer after reading for size check
            
            if not validation['success']:
                return validation
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create client-specific subdirectory
            client_upload_dir = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f'client_{client_id}'
            )
            os.makedirs(client_upload_dir, exist_ok=True)
            
            file_path = os.path.join(client_upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(original_filename)
            
            # Handle existing document for this item
            existing_doc = ClientDocument.query.filter_by(
                client_id=client_id,
                checklist_item_id=item_id
            ).first()
            
            if existing_doc:
                # Remove old file
                if os.path.exists(existing_doc.file_path):
                    os.remove(existing_doc.file_path)
                db.session.delete(existing_doc)
            
            # Create new document record
            document = ClientDocument(
                client_id=client_id,
                checklist_item_id=item_id,
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by_client=True
            )
            
            db.session.add(document)
            
            # Update item status
            item.status = 'uploaded'
            item.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'File uploaded successfully',
                'filename': original_filename,
                'document_id': document.id
            }
            
        except Exception as e:
            db.session.rollback()
            # Clean up file if database operation fails
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            return {
                'success': False,
                'message': f'Upload error: {str(e)}'
            }
    

    def update_item_status(self, item_id: int, client_id: int, new_status: str) -> Dict[str, Any]:
        """
        Update document item status
        
        Args:
            item_id: The checklist item ID
            client_id: The client's ID
            new_status: The new status value
            
        Returns:
            Dict containing update results
        """
        try:
            # Validate status
            valid_statuses = ['already_provided', 'not_applicable', 'pending', 'uploaded']
            if new_status not in valid_statuses:
                return {
                    'success': False,
                    'message': 'Invalid status selected'
                }
            
            # Verify checklist item access
            verification = PortalService.verify_checklist_item_access(item_id, client_id)
            if not verification['success']:
                return verification
            
            item = verification['item']
            
            # If changing from uploaded status, remove the uploaded file
            if item.status == 'uploaded' and new_status != 'uploaded':
                existing_doc = ClientDocument.query.filter_by(
                    client_id=client_id,
                    checklist_item_id=item_id
                ).first()
                
                if existing_doc:
                    # Remove file
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
                'pending': 'Reset to pending',
                'uploaded': 'Marked as uploaded'
            }
            
            return {
                'success': True,
                'message': status_messages.get(new_status, 'Status updated'),
                'new_status': new_status
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating status: {str(e)}'
            }
    

    def get_client_document(self, document_id: int, client_id: int) -> Dict[str, Any]:
        """
        Get a client document with access verification
        
        Args:
            document_id: The document ID
            client_id: The client's ID
            
        Returns:
            Dict containing document data or error
        """
        try:
            document = ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).filter(
                ClientDocument.id == document_id,
                DocumentChecklist.client_id == client_id
            ).first()
            
            if not document:
                return {
                    'success': False,
                    'message': 'Document not found or access denied',
                    'document': None
                }
            
            return {
                'success': True,
                'document': document
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving document: {str(e)}',
                'document': None
            }
    

    def get_client_by_id(self, client_id: int) -> Optional[Client]:
        """
        Get a client by ID
        
        Args:
            client_id: The client's ID
            
        Returns:
            Client object if found, None otherwise
        """
        return Client.query.get(client_id)
    

    def get_client_statistics(self, client_id: int) -> Dict[str, Any]:
        """
        Get statistics for a client's document checklists
        
        Args:
            client_id: The client's ID
            
        Returns:
            Dict containing statistics
        """
        try:
            checklists = DocumentChecklist.query.filter_by(
                client_id=client_id,
                is_active=True
            ).all()
            
            total_items = 0
            completed_items = 0
            pending_items = 0
            uploaded_items = 0
            
            for checklist in checklists:
                items = ChecklistItem.query.filter_by(checklist_id=checklist.id).all()
                total_items += len(items)
                
                for item in items:
                    if item.status == 'uploaded':
                        uploaded_items += 1
                        completed_items += 1
                    elif item.status in ['already_provided', 'not_applicable']:
                        completed_items += 1
                    else:
                        pending_items += 1
            
            return {
                'success': True,
                'statistics': {
                    'total_checklists': len(checklists),
                    'total_items': total_items,
                    'completed_items': completed_items,
                    'pending_items': pending_items,
                    'uploaded_items': uploaded_items,
                    'completion_percentage': (completed_items / total_items * 100) if total_items > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting statistics: {str(e)}',
                'statistics': {}
            }
    

    def validate_session_data(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate client session data
        
        Args:
            session_data: Session data to validate
            
        Returns:
            Dict containing validation results
        """
        required_fields = ['client_user_id', 'client_id', 'client_email']
        
        for field in required_fields:
            if field not in session_data:
                return {
                    'success': False,
                    'message': f'Missing session data: {field}',
                    'authenticated': False
                }
        
        # Verify client user still exists and is active
        client_user = ClientUser.query.filter_by(
            id=session_data['client_user_id'],
            is_active=True
        ).first()
        
        if not client_user:
            return {
                'success': False,
                'message': 'Client user not found or inactive',
                'authenticated': False
            }
        
        return {
            'success': True,
            'message': 'Session validated',
            'authenticated': True,
            'client_user': client_user
        }