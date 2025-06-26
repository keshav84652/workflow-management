"""
Attachment Service for handling file uploads and management
Centralized business logic for file operations
"""

import os
import uuid
import mimetypes
import logging
from typing import Dict, Any, Optional, Tuple
from werkzeug.utils import secure_filename

import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Task, Project, Attachment
from services.activity_service import ActivityService


class AttachmentService:
    """Service for handling file attachments and uploads"""
    
    def __init__(self, config=None):
        """Initialize attachment service with configuration"""
        self.config = config
    
    def is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        if not self.config or 'ALLOWED_EXTENSIONS' not in self.config:
            # Default allowed extensions if config not available
            allowed = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
        else:
            allowed = self.config['ALLOWED_EXTENSIONS']
        
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed
    
    def save_uploaded_file(self, file, firm_id: int, entity_type: str, entity_id: int, uploaded_by: int) -> Tuple[Optional[Attachment], Optional[str]]:
        """Save uploaded file and create attachment record"""
        file_path = None
        try:
            if not file or not self.is_allowed_file(file.filename):
                return None, "Invalid file type"
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Create firm-specific subdirectory
            upload_folder = self.config.get('UPLOAD_FOLDER', 'uploads') if self.config else 'uploads'
            firm_upload_dir = os.path.join(upload_folder, str(firm_id))
            os.makedirs(firm_upload_dir, exist_ok=True)
            
            file_path = os.path.join(firm_upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(original_filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Create attachment record with correct field names
            attachment = Attachment(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by=uploaded_by,
                firm_id=firm_id
            )
            
            # Set entity-specific foreign keys
            if entity_type == 'task':
                attachment.task_id = entity_id
            elif entity_type == 'project':
                attachment.project_id = entity_id
            
            db.session.add(attachment)
            db.session.commit()
            
            logging.info(f"File uploaded successfully: {original_filename} -> {file_path}")
            return attachment, None
            
        except Exception as e:
            db.session.rollback()
            # Clean up file if database operation fails
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            logging.error(f"Failed to save uploaded file: {str(e)}")
            return None, f"Upload failed: {str(e)}"
    
    def delete_attachment(self, attachment_id: int, firm_id: int) -> Tuple[bool, Optional[str]]:
        """Delete an attachment and its file"""
        try:
            # Get attachment and verify firm access
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                firm_id=firm_id
            ).first()
            
            if not attachment:
                return False, "Attachment not found"
            
            # Delete physical file if it exists
            if attachment.file_path and os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)
                    logging.info(f"Deleted file: {attachment.file_path}")
                except OSError as e:
                    logging.warning(f"Could not delete file {attachment.file_path}: {e}")
            
            # Get entity info for activity log before deletion
            entity_type = attachment.entity_type
            entity_id = attachment.entity_id
            filename = attachment.original_filename
            
            # Delete database record
            db.session.delete(attachment)
            db.session.commit()
            
            # Create activity log (Note: Need user_id for proper activity logging)
            # This method needs to be updated to accept user_id parameter
            # ActivityService.create_activity_log(
            #     action=f"Deleted attachment: {filename}",
            #     user_id=user_id,
            #     project_id=project_id,
            #     task_id=entity_id if entity_type == 'task' else None
            # )
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to delete attachment {attachment_id}: {str(e)}")
            return False, f"Delete failed: {str(e)}"
    
    def get_attachment_file_path(self, attachment_id: int, firm_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get file path for downloading an attachment"""
        try:
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                firm_id=firm_id
            ).first()
            
            if not attachment:
                return None, None, "Attachment not found"
            
            if not attachment.file_path or not os.path.exists(attachment.file_path):
                return None, None, "File not found on server"
            
            return attachment.file_path, attachment.original_filename, None
            
        except Exception as e:
            logging.error(f"Failed to get attachment file path: {str(e)}")
            return None, None, f"Error: {str(e)}"
    
    def upload_file(self, file, entity_type: str, entity_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Upload file for a task or project"""
        try:
            # Verify entity exists and user has access
            if entity_type == 'task':
                task = Task.query.get(entity_id)
                if not task:
                    return {'success': False, 'message': 'Task not found'}
                
                # Check firm access through project or direct task
                if task.project and task.project.firm_id != firm_id:
                    return {'success': False, 'message': 'Access denied'}
                elif not task.project and task.firm_id != firm_id:
                    return {'success': False, 'message': 'Access denied'}
                
                entity_name = task.title
                project_id = task.project_id if task.project else None
                
            elif entity_type == 'project':
                project = Project.query.get(entity_id)
                if not project:
                    return {'success': False, 'message': 'Project not found'}
                
                if project.firm_id != firm_id:
                    return {'success': False, 'message': 'Access denied'}
                
                entity_name = project.name
                project_id = project.id
                
            else:
                return {'success': False, 'message': 'Invalid entity type'}
            
            # Save the file
            attachment, error = self.save_uploaded_file(file, firm_id, entity_type, entity_id, user_id)
            
            if error:
                return {'success': False, 'message': error}
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'File "{attachment.original_filename}" uploaded to {entity_type} "{entity_name}"',
                user_id=user_id,
                project_id=project_id,
                task_id=entity_id if entity_type == 'task' else None
            )
            
            return {
                'success': True,
                'attachment': {
                    'id': attachment.id,
                    'original_filename': attachment.original_filename,
                    'file_size_formatted': attachment.file_size_formatted if hasattr(attachment, 'file_size_formatted') else str(attachment.file_size),
                    'uploaded_at': attachment.uploaded_at.strftime('%m/%d/%Y %I:%M %p'),
                    'uploader_name': attachment.uploader.name if hasattr(attachment, 'uploader') else 'Unknown'
                }
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Upload failed: {str(e)}'}
    
    def download_attachment(self, attachment_id: int, firm_id: int, user_id: int) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Get attachment file for download and log the activity"""
        try:
            attachment = Attachment.query.get(attachment_id)
            
            if not attachment:
                return None, None, None, 'Attachment not found'
            
            # Check firm access
            if attachment.firm_id != firm_id:
                return None, None, None, 'Access denied'
            
            if not os.path.exists(attachment.file_path):
                return None, None, None, 'File not found'
            
            # Create activity log
            entity_type = 'task' if attachment.task_id else 'project'
            entity_name = attachment.task.title if attachment.task_id else attachment.project.name
            ActivityService.create_activity_log(
                action=f'File "{attachment.original_filename}" downloaded from {entity_type} "{entity_name}"',
                user_id=user_id,
                project_id=attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None),
                task_id=attachment.task_id
            )
            
            return attachment.file_path, attachment.original_filename, attachment.mime_type, None
            
        except Exception as e:
            logging.error(f"Failed to download attachment: {str(e)}")
            return None, None, None, f'Download failed: {str(e)}'
    
    def delete_attachment_with_activity_log(self, attachment_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Delete attachment with activity logging"""
        try:
            attachment = Attachment.query.get(attachment_id)
            
            if not attachment:
                return {'success': False, 'message': 'Attachment not found'}
            
            # Check firm access
            if attachment.firm_id != firm_id:
                return {'success': False, 'message': 'Access denied'}
            
            # Get info for activity log before deletion
            entity_type = 'task' if attachment.task_id else 'project'
            entity_name = attachment.task.title if attachment.task_id else attachment.project.name
            filename = attachment.original_filename
            project_id = attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None)
            task_id = attachment.task_id
            
            # Delete physical file
            if os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
            
            # Delete database record
            db.session.delete(attachment)
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'File "{filename}" deleted from {entity_type} "{entity_name}"',
                user_id=user_id,
                project_id=project_id,
                task_id=task_id
            )
            
            return {'success': True, 'message': 'File deleted successfully'}
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to delete attachment: {str(e)}")
            return {'success': False, 'message': f'Delete failed: {str(e)}'}