"""
Client portal blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

from core import db
from models import (
    ClientUser, Client, DocumentChecklist, ChecklistItem, ClientDocument
)

client_portal_bp = Blueprint('client_portal', __name__)


def allowed_file_local(filename):
    """Check if file extension is allowed"""
    from flask import current_app
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@client_portal_bp.route('/client-portal')
@client_portal_bp.route('/client-login')
def client_login():
    """Client portal login page"""
    return render_template('clients/client_login.html')


@client_portal_bp.route('/client-authenticate', methods=['POST'])
def client_authenticate():
    """Authenticate client user"""
    access_code = request.form.get('access_code', '').strip()
    client_user = ClientUser.query.filter_by(access_code=access_code, is_active=True).first()
    
    if client_user:
        session['client_user_id'] = client_user.id
        session['client_id'] = client_user.client_id
        session['client_email'] = client_user.email
        client_user.last_login = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('client_portal.client_dashboard'))
    else:
        flash('Invalid access code', 'error')
        return redirect(url_for('client_portal.client_login'))


@client_portal_bp.route('/client-dashboard')
def client_dashboard():
    """Client portal dashboard"""
    if 'client_user_id' not in session:
        return redirect(url_for('client_portal.client_login'))
    
    client_id = session['client_id']
    client = Client.query.get(client_id)
    
    # Get active checklists for this client
    checklists = DocumentChecklist.query.filter_by(
        client_id=client_id, 
        is_active=True
    ).all()
    
    return render_template('clients/client_dashboard_modern.html', client=client, checklists=checklists)


@client_portal_bp.route('/client-logout')
def client_logout():
    """Client logout"""
    session.pop('client_user_id', None)
    session.pop('client_id', None)
    session.pop('client_email', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('client_portal.client_login'))


@client_portal_bp.route('/client-upload/<int:item_id>', methods=['POST'])
def client_upload_document(item_id):
    """Handle client document upload"""
    if 'client_user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    client_id = session['client_id']
    
    # Verify the checklist item belongs to this client
    item = ChecklistItem.query.join(DocumentChecklist).filter(
        ChecklistItem.id == item_id,
        DocumentChecklist.client_id == client_id
    ).first()
    
    if not item:
        return jsonify({'success': False, 'message': 'Invalid document item'}), 404
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file_local(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed'}), 400
    
    try:
        from flask import current_app
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create client-specific subdirectory
        client_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'client_{client_id}')
        os.makedirs(client_upload_dir, exist_ok=True)
        
        file_path = os.path.join(client_upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Delete any existing document for this item
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
        
        return jsonify({
            'success': True, 
            'message': 'File uploaded successfully',
            'filename': original_filename
        })
        
    except Exception as e:
        db.session.rollback()
        # Clean up file if database operation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': str(e)}), 500


@client_portal_bp.route('/client-update-status/<int:item_id>', methods=['POST'])
def client_update_status(item_id):
    """Update document item status (already provided, not applicable)"""
    if 'client_user_id' not in session:
        flash('Not authenticated', 'error')
        return redirect(url_for('client_portal.client_login'))
    
    client_id = session['client_id']
    new_status = request.form.get('status')
    
    if new_status not in ['already_provided', 'not_applicable', 'pending']:
        flash('Invalid status selected', 'error')
        return redirect(url_for('client_portal.client_dashboard'))
    
    # Verify the checklist item belongs to this client
    item = ChecklistItem.query.join(DocumentChecklist).filter(
        ChecklistItem.id == item_id,
        DocumentChecklist.client_id == client_id
    ).first()
    
    if not item:
        flash('Document not found', 'error')
        return redirect(url_for('client_portal.client_dashboard'))
    
    try:
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
            'pending': 'Reset to pending'
        }
        
        flash(status_messages.get(new_status, 'Status updated'), 'success')
        return redirect(url_for('client_portal.client_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('client_portal.client_dashboard'))