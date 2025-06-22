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

from core import db
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