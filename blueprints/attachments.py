"""
File attachment handling blueprint
"""

from flask import Blueprint, request, redirect, url_for, session, flash, jsonify, send_file
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

from core import db
from models import Task, Project, Attachment
from utils import create_activity_log

attachments_bp = Blueprint('attachments', __name__, url_prefix='/attachments')


def allowed_file_local(filename):
    """Check if file extension is allowed"""
    from flask import current_app
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file, firm_id, entity_type, entity_id):
    """Save uploaded file and create attachment record"""
    from flask import current_app
    
    if not file or not allowed_file_local(file.filename):
        return None, "Invalid file type"
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Create firm-specific subdirectory
    firm_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(firm_id))
    os.makedirs(firm_upload_dir, exist_ok=True)
    
    file_path = os.path.join(firm_upload_dir, unique_filename)
    
    try:
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Create attachment record
        attachment = Attachment(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=session['user_id'],
            firm_id=firm_id
        )
        
        if entity_type == 'task':
            attachment.task_id = entity_id
        elif entity_type == 'project':
            attachment.project_id = entity_id
        
        db.session.add(attachment)
        db.session.commit()
        
        return attachment, None
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, str(e)


@attachments_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for tasks and projects"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    entity_type = request.form.get('entity_type')  # 'task' or 'project'
    entity_id = request.form.get('entity_id')
    
    if not entity_type or not entity_id:
        return jsonify({'success': False, 'message': 'Missing entity information'}), 400
    
    firm_id = session['firm_id']
    
    # Verify entity belongs to firm
    if entity_type == 'task':
        task = Task.query.get_or_404(entity_id)
        if task.project and task.project.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        elif not task.project and task.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif entity_type == 'project':
        project = Project.query.get_or_404(entity_id)
        if project.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        return jsonify({'success': False, 'message': 'Invalid entity type'}), 400
    
    # Save file
    attachment, error = save_uploaded_file(file, firm_id, entity_type, entity_id)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    # Activity log
    entity_name = task.title if entity_type == 'task' else project.name
    create_activity_log(
        f'File "{attachment.original_filename}" uploaded to {entity_type} "{entity_name}"',
        session['user_id'],
        project.id if entity_type == 'project' else (task.project_id if task.project else None),
        task.id if entity_type == 'task' else None
    )
    
    return jsonify({
        'success': True,
        'attachment': {
            'id': attachment.id,
            'original_filename': attachment.original_filename,
            'file_size_formatted': attachment.file_size_formatted,
            'uploaded_at': attachment.uploaded_at.strftime('%m/%d/%Y %I:%M %p'),
            'uploader_name': attachment.uploader.name
        }
    })


@attachments_bp.route('/<int:attachment_id>/download')
def download_attachment(attachment_id):
    """Download an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Check access
    if attachment.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.main'))
    
    if not os.path.exists(attachment.file_path):
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('dashboard.main'))
    
    # Activity log
    entity_type = 'task' if attachment.task_id else 'project'
    entity_name = attachment.task.title if attachment.task_id else attachment.project.name
    create_activity_log(
        f'File "{attachment.original_filename}" downloaded from {entity_type} "{entity_name}"',
        session['user_id'],
        attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None),
        attachment.task_id
    )
    
    return send_file(
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.original_filename,
        mimetype=attachment.mime_type
    )


@attachments_bp.route('/<int:attachment_id>/delete', methods=['POST'])
def delete_attachment(attachment_id):
    """Delete an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Check access
    if attachment.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Delete physical file
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
        
        # Activity log
        entity_type = 'task' if attachment.task_id else 'project'
        entity_name = attachment.task.title if attachment.task_id else attachment.project.name
        create_activity_log(
            f'File "{attachment.original_filename}" deleted from {entity_type} "{entity_name}"',
            session['user_id'],
            attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None),
            attachment.task_id
        )
        
        # Delete database record
        db.session.delete(attachment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500