"""
Document and checklist service layer for business logic
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from flask import session
from werkzeug.utils import secure_filename
import os
import uuid
import mimetypes

from core.db_import import db
from models import (
    DocumentChecklist, ChecklistItem, Client, ClientDocument, 
    ClientUser, Attachment, User, ClientChecklistAccess
)
from utils import create_activity_log


class DocumentService:
    """Service class for document and checklist-related business operations"""
    
    @staticmethod
    def get_checklists_for_firm(firm_id: int) -> List[DocumentChecklist]:
        """
        Get all document checklists for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of DocumentChecklist objects for the firm
        """
        return DocumentChecklist.query.join(Client).filter(
            Client.firm_id == firm_id
        ).all()
    
    @staticmethod
    def get_checklist_by_id(checklist_id: int, firm_id: int) -> Optional[DocumentChecklist]:
        """
        Get a checklist by ID, ensuring it belongs to the firm
        
        Args:
            checklist_id: The checklist's ID
            firm_id: The firm's ID for security check
            
        Returns:
            DocumentChecklist object if found and belongs to firm, None otherwise
        """
        return DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
    
    @staticmethod
    def create_checklist(client_id: int, name: str, description: str, 
                        firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a new document checklist
        
        Args:
            client_id: The client's ID
            name: Checklist name
            description: Checklist description
            firm_id: The firm's ID for security check
            user_id: The creating user's ID
            
        Returns:
            Dict containing success status, checklist data, and any error messages
        """
        try:
            # Verify client belongs to this firm
            client = Client.query.filter_by(id=client_id, firm_id=firm_id).first()
            if not client:
                return {
                    'success': False,
                    'message': 'Invalid client selected',
                    'checklist': None
                }
            
            checklist = DocumentChecklist(
                client_id=client_id,
                name=name,
                description=description,
                created_by=user_id,
                is_active=True
            )
            
            db.session.add(checklist)
            db.session.commit()
            
            # Create activity log
            create_activity_log(
                user_id=user_id,
                firm_id=firm_id,
                action='create',
                details=f'Created checklist "{name}" for client {client.name}'
            )
            
            return {
                'success': True,
                'message': f'Checklist "{name}" created successfully for {client.name}',
                'checklist': {
                    'id': checklist.id,
                    'name': checklist.name,
                    'client_name': client.name
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating checklist: {str(e)}',
                'checklist': None
            }
    
    @staticmethod
    def update_checklist(checklist_id: int, name: str, description: str,
                        firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update a document checklist's basic information
        
        Args:
            checklist_id: The checklist's ID
            name: Updated checklist name
            description: Updated checklist description
            firm_id: The firm's ID for security check
            user_id: The updating user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            old_name = checklist.name
            checklist.name = name
            checklist.description = description
            
            db.session.commit()
            
            # Create activity log if name changed
            if old_name != name:
                create_activity_log(
                    user_id=user_id,
                    firm_id=firm_id,
                    action='update',
                    details=f'Updated checklist name from "{old_name}" to "{name}"'
                )
            
            return {
                'success': True,
                'message': 'Checklist updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating checklist: {str(e)}'
            }
    
    @staticmethod
    def add_checklist_item(checklist_id: int, item_name: str, description: str,
                          firm_id: int, user_id: int, is_required: bool = True,
                          order_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Add an item to a document checklist
        
        Args:
            checklist_id: The checklist's ID
            item_name: Name of the checklist item
            description: Description of the item
            firm_id: The firm's ID for security check
            user_id: The creating user's ID
            is_required: Whether the item is required
            order_index: Position in the checklist
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            # If no order specified, add at the end
            if order_index is None:
                max_order = db.session.query(db.func.max(ChecklistItem.order_index)).filter_by(
                    checklist_id=checklist_id
                ).scalar() or 0
                order_index = max_order + 1
            
            item = ChecklistItem(
                checklist_id=checklist_id,
                name=item_name,
                description=description,
                is_required=is_required,
                order_index=order_index
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Create activity log
            create_activity_log(
                user_id=user_id,
                firm_id=firm_id,
                action='create',
                details=f'Added item "{item_name}" to checklist "{checklist.name}"'
            )
            
            return {
                'success': True,
                'message': f'Item "{item_name}" added successfully',
                'item_id': item.id
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error adding checklist item: {str(e)}'
            }
    
    @staticmethod
    def update_checklist_item(item_id: int, item_name: str, description: str,
                             is_required: bool, checklist_id: int, firm_id: int,
                             user_id: int) -> Dict[str, Any]:
        """
        Update a checklist item
        
        Args:
            item_id: The item's ID
            item_name: Updated item name
            description: Updated item description
            is_required: Whether the item is required
            checklist_id: The checklist's ID for security check
            firm_id: The firm's ID for security check
            user_id: The updating user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            # Verify checklist belongs to firm
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            item = ChecklistItem.query.filter_by(
                id=item_id,
                checklist_id=checklist_id
            ).first()
            
            if not item:
                return {
                    'success': False,
                    'message': 'Checklist item not found'
                }
            
            old_name = item.name
            item.name = item_name
            item.description = description
            item.is_required = is_required
            
            db.session.commit()
            
            # Create activity log if name changed
            if old_name != item_name:
                create_activity_log(
                    user_id=user_id,
                    firm_id=firm_id,
                    action='update',
                    details=f'Updated checklist item from "{old_name}" to "{item_name}"'
                )
            
            return {
                'success': True,
                'message': 'Checklist item updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating checklist item: {str(e)}'
            }
    
    @staticmethod
    def delete_checklist_item(item_id: int, checklist_id: int, firm_id: int,
                             user_id: int) -> Dict[str, Any]:
        """
        Delete a checklist item
        
        Args:
            item_id: The item's ID
            checklist_id: The checklist's ID for security check
            firm_id: The firm's ID for security check
            user_id: The deleting user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            # Verify checklist belongs to firm
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            item = ChecklistItem.query.filter_by(
                id=item_id,
                checklist_id=checklist_id
            ).first()
            
            if not item:
                return {
                    'success': False,
                    'message': 'Checklist item not found'
                }
            
            item_name = item.name
            db.session.delete(item)
            db.session.commit()
            
            # Create activity log
            create_activity_log(
                user_id=user_id,
                firm_id=firm_id,
                action='delete',
                details=f'Deleted checklist item "{item_name}" from "{checklist.name}"'
            )
            
            return {
                'success': True,
                'message': f'Item "{item_name}" deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error deleting checklist item: {str(e)}'
            }
    
    @staticmethod
    def get_checklist_items(checklist_id: int, firm_id: int) -> List[ChecklistItem]:
        """
        Get all items for a checklist
        
        Args:
            checklist_id: The checklist's ID
            firm_id: The firm's ID for security check
            
        Returns:
            List of ChecklistItem objects ordered by order_index
        """
        # Verify checklist belongs to firm first
        checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
        if not checklist:
            return []
        
        return ChecklistItem.query.filter_by(
            checklist_id=checklist_id
        ).order_by(ChecklistItem.order_index).all()
    
    @staticmethod
    def create_client_access(checklist_id: int, firm_id: int, user_id: int,
                            password: Optional[str] = None) -> Dict[str, Any]:
        """
        Create client access for a checklist
        
        Args:
            checklist_id: The checklist's ID
            firm_id: The firm's ID for security check
            user_id: The creating user's ID
            password: Optional password for access
            
        Returns:
            Dict containing success status, access data, and any error messages
        """
        try:
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found',
                    'access': None
                }
            
            # Generate unique access token
            access_token = str(uuid.uuid4())
            
            access = ClientChecklistAccess(
                checklist_id=checklist_id,
                access_token=access_token,
                password=password,
                is_active=True,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(access)
            db.session.commit()
            
            # Create activity log
            create_activity_log(
                user_id=user_id,
                firm_id=firm_id,
                action='create',
                details=f'Created client access for checklist "{checklist.name}"'
            )
            
            return {
                'success': True,
                'message': 'Client access created successfully',
                'access': {
                    'id': access.id,
                    'access_token': access.access_token,
                    'has_password': bool(password)
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating client access: {str(e)}',
                'access': None
            }
    
    @staticmethod
    def validate_file_upload(filename: str, file_size: int, 
                           allowed_extensions: set) -> Tuple[bool, str]:
        """
        Validate file upload requirements
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            allowed_extensions: Set of allowed file extensions
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "No file selected"
        
        # Check file extension
        if '.' not in filename:
            return False, "File must have an extension"
        
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            return False, f"File type '{extension}' not allowed"
        
        # Check file size (16MB limit)
        max_size = 16 * 1024 * 1024  # 16MB
        if file_size > max_size:
            return False, f"File size too large. Maximum {max_size // (1024*1024)}MB allowed"
        
        return True, ""
    
    @staticmethod
    def update_checklist_with_items(checklist_id: int, name: str, description: str,
                                   items_data: Dict[str, Any], firm_id: int, 
                                   user_id: int) -> Dict[str, Any]:
        """
        Update a checklist and its items in a single transaction
        
        Args:
            checklist_id: The checklist's ID
            name: Updated checklist name
            description: Updated checklist description
            items_data: Dict containing item updates, deletions, and additions
            firm_id: The firm's ID for security check
            user_id: The updating user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found or access denied'
                }
            
            # Update basic checklist info
            checklist.name = name
            checklist.description = description
            
            # Handle deleted items first
            deleted_item_ids = items_data.get('deleted_item_ids', [])
            for item_id in deleted_item_ids:
                if item_id:
                    item = ChecklistItem.query.filter_by(
                        id=item_id, 
                        checklist_id=checklist_id
                    ).first()
                    if item:
                        db.session.delete(item)
            
            # Handle existing items updates
            item_ids = items_data.get('item_ids', [])
            item_titles = items_data.get('item_titles', [])
            item_descriptions = items_data.get('item_descriptions', [])
            item_required = items_data.get('item_required', [])
            item_sort_orders = items_data.get('item_sort_orders', [])
            
            # Update existing items
            for i, item_id in enumerate(item_ids):
                if item_id and i < len(item_titles):
                    item = ChecklistItem.query.filter_by(
                        id=item_id, 
                        checklist_id=checklist_id
                    ).first()
                    
                    if item:
                        item.title = item_titles[i] if i < len(item_titles) else item.title
                        item.description = item_descriptions[i] if i < len(item_descriptions) else ''
                        item.is_required = str(i) in item_required
                        item.sort_order = int(item_sort_orders[i]) if i < len(item_sort_orders) and item_sort_orders[i] else item.sort_order
                
                elif not item_id and i < len(item_titles) and item_titles[i].strip():
                    # This is a new item (no ID but has title)
                    max_order = db.session.query(db.func.max(ChecklistItem.sort_order)).filter_by(
                        checklist_id=checklist_id
                    ).scalar() or 0
                    
                    new_item = ChecklistItem(
                        checklist_id=checklist_id,
                        title=item_titles[i],
                        description=item_descriptions[i] if i < len(item_descriptions) else '',
                        is_required=str(i) in item_required,
                        sort_order=int(item_sort_orders[i]) if i < len(item_sort_orders) and item_sort_orders[i] else max_order + 1
                    )
                    db.session.add(new_item)
            
            db.session.commit()
            
            # Log activity
            create_activity_log(
                action=f'Updated checklist: {name}',
                user_id=user_id,
                details=f'Updated checklist and items for {checklist.client.name}'
            )
            
            return {
                'success': True,
                'message': 'Checklist and items updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating checklist: {str(e)}'
            }

    @staticmethod
    def get_document_for_download(document_id: int, firm_id: int) -> Optional[ClientDocument]:
        """
        Get a document for download with security verification
        
        Args:
            document_id: The document's ID
            firm_id: The firm's ID for security check
            
        Returns:
            ClientDocument if found and accessible, None otherwise
        """
        from models import ClientDocument, ChecklistItem, DocumentChecklist, Client
        
        return ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()

    @staticmethod
    def upload_file_to_checklist_item(file, token: str, item_id: int) -> Dict[str, Any]:
        """
        Handle file upload for checklist items with comprehensive validation and transaction management
        
        Args:
            file: Uploaded file object
            token: Public checklist token
            item_id: Checklist item ID
            
        Returns:
            Dict containing success status and any error messages
        """
        import uuid
        import mimetypes
        from datetime import datetime
        from werkzeug.utils import secure_filename
        from models import DocumentChecklist, ChecklistItem, ClientDocument
        
        try:
            # Validate checklist and item exist
            checklist = DocumentChecklist.query.filter_by(public_token=token).first()
            if not checklist:
                return {
                    'success': False,
                    'message': 'Invalid checklist'
                }
            
            item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first()
            if not item:
                return {
                    'success': False,
                    'message': 'Invalid checklist item'
                }
            
            # Validate file
            if not file or file.filename == '':
                return {
                    'success': False,
                    'message': 'No file selected'
                }
            
            # Validate file type and size
            original_filename = secure_filename(file.filename)
            if not original_filename:
                return {
                    'success': False,
                    'message': 'Invalid filename'
                }
            
            # Check file extension
            if '.' not in original_filename:
                return {
                    'success': False,
                    'message': 'File must have an extension'
                }
            
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'xls'}
            if file_extension not in allowed_extensions:
                return {
                    'success': False,
                    'message': f'File type .{file_extension} not allowed. Allowed types: {", ".join(allowed_extensions)}'
                }
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create client-specific subdirectory
            from flask import current_app
            client_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'client_{checklist.client_id}')
            os.makedirs(client_upload_dir, exist_ok=True)
            
            file_path = os.path.join(client_upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Validate file size (10MB limit)
            max_file_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_file_size:
                os.remove(file_path)  # Clean up
                return {
                    'success': False,
                    'message': 'File size too large. Maximum size is 10MB.'
                }
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(original_filename)
            
            # Database transaction
            try:
                # Delete any existing document for this item
                existing_doc = ClientDocument.query.filter_by(
                    client_id=checklist.client_id,
                    checklist_item_id=item_id
                ).first()
                
                if existing_doc:
                    # Remove old file
                    if os.path.exists(existing_doc.file_path):
                        os.remove(existing_doc.file_path)
                    db.session.delete(existing_doc)
                
                # Create new document record
                document = ClientDocument(
                    client_id=checklist.client_id,
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
                    'document': {
                        'id': document.id,
                        'filename': document.original_filename,
                        'file_size': document.file_size
                    }
                }
                
            except Exception as db_error:
                db.session.rollback()
                # Clean up file if database operation fails
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise db_error
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Upload failed: {str(e)}'
            }

    @staticmethod
    def get_secure_filename(filename: str) -> str:
        """
        Generate a secure filename for file uploads
        
        Args:
            filename: Original filename
            
        Returns:
            Secure filename with UUID prefix
        """
        # Get secure filename and add UUID to prevent conflicts
        secure_name = secure_filename(filename)
        unique_id = str(uuid.uuid4()).replace('-', '')[:16]
        return f"{unique_id}_{secure_name}"