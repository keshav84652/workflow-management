"""
File attachment handling blueprint
"""

from flask import Blueprint, request, redirect, url_for, session, flash, jsonify, send_file, current_app

from services.attachment_service import AttachmentService

attachments_bp = Blueprint('attachments', __name__, url_prefix='/attachments')


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
    
    try:
        entity_id = int(entity_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid entity ID'}), 400
    
    firm_id = session['firm_id']
    user_id = session['user_id']
    
    # Initialize attachment service
    attachment_service = AttachmentService(current_app.config)
    
    # Upload file using service
    result = attachment_service.upload_file(file, entity_type, entity_id, firm_id, user_id)
    
    if not result['success']:
        return jsonify(result), 400 if 'Access denied' not in result['message'] else 403
    
    return jsonify(result)


@attachments_bp.route('/<int:attachment_id>/download')
def download_attachment(attachment_id):
    """Download an attachment"""
    firm_id = session['firm_id']
    user_id = session['user_id']
    
    # Initialize attachment service
    attachment_service = AttachmentService(current_app.config)
    
    # Get attachment file info
    file_path, original_filename, mime_type, error = attachment_service.download_attachment(
        attachment_id, firm_id, user_id
    )
    
    if error:
        flash(error, 'error')
        return redirect(request.referrer or url_for('dashboard.main'))
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=original_filename,
        mimetype=mime_type
    )


@attachments_bp.route('/<int:attachment_id>/delete', methods=['POST'])
def delete_attachment(attachment_id):
    """Delete an attachment"""
    firm_id = session['firm_id']
    user_id = session['user_id']
    
    # Initialize attachment service
    attachment_service = AttachmentService(current_app.config)
    
    # Delete attachment using service
    result = attachment_service.delete_attachment_with_activity_log(attachment_id, firm_id, user_id)
    
    if not result['success']:
        return jsonify(result), 403 if 'Access denied' in result['message'] else 500
    
    return jsonify(result)