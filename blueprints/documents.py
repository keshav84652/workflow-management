"""
Document and checklist management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

from core import db
from models import (
    DocumentChecklist, ChecklistItem, Client, ClientDocument, 
    ClientUser, Attachment, User, ClientChecklistAccess
)
from utils import create_activity_log

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/checklists')
@documents_bp.route('/document_checklists')  # Legacy URL support
def document_checklists():
    """CPA view to manage document checklists"""
    firm_id = session['firm_id']
    
    # Get all checklists for the firm
    checklists = DocumentChecklist.query.join(Client).filter(
        Client.firm_id == firm_id
    ).all()
    
    # Get all clients for creating new checklists
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    return render_template('documents/document_checklists.html', checklists=checklists, clients=clients)


@documents_bp.route('/create-checklist', methods=['GET', 'POST'])
def create_checklist():
    """Create a new document checklist"""
    firm_id = session['firm_id']
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Verify client belongs to this firm
        client = Client.query.filter_by(id=client_id, firm_id=firm_id).first()
        if not client:
            flash('Invalid client selected', 'error')
            return redirect(url_for('documents.document_checklists'))
        
        checklist = DocumentChecklist(
            client_id=client_id,
            name=name,
            description=description,
            created_by=session['user_id'],
            is_active=True
        )
        
        db.session.add(checklist)
        db.session.commit()
        
        flash(f'Checklist "{name}" created successfully for {client.name}', 'success')
        return redirect(url_for('documents.edit_checklist', checklist_id=checklist.id))
    
    # GET request - show form
    clients = Client.query.filter_by(firm_id=firm_id).all()
    return render_template('documents/create_checklist_modern.html', clients=clients)


@documents_bp.route('/edit-checklist/<int:checklist_id>', methods=['GET', 'POST'])
def edit_checklist(checklist_id):
    """Edit a document checklist and its items"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # If no specific action, this is the main form submission (Save Changes button)
        if not action:
            # Update basic checklist info
            checklist.name = request.form.get('name')
            checklist.description = request.form.get('description', '')
            
            # Handle deleted items first
            deleted_item_ids = request.form.getlist('deleted_item_ids[]')
            for item_id in deleted_item_ids:
                if item_id:
                    item = ChecklistItem.query.filter_by(
                        id=item_id, 
                        checklist_id=checklist_id
                    ).first()
                    if item:
                        db.session.delete(item)
            
            # Handle existing items updates
            item_ids = request.form.getlist('item_ids[]')
            item_titles = request.form.getlist('item_titles[]')
            item_descriptions = request.form.getlist('item_descriptions[]')
            item_required = request.form.getlist('item_required[]')
            item_sort_orders = request.form.getlist('item_sort_orders[]')
            
            # Update existing items
            for i, item_id in enumerate(item_ids):
                if item_id and i < len(item_titles):  # Only process if we have an ID and title
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
            flash('Checklist and items updated successfully', 'success')
            return redirect(url_for('documents.edit_checklist', checklist_id=checklist_id))
        
        elif action == 'update_checklist':
            checklist.name = request.form.get('name')
            checklist.description = request.form.get('description', '')
            db.session.commit()
            flash('Checklist updated successfully', 'success')
            
        elif action == 'add_item':
            title = request.form.get('title')
            description = request.form.get('description', '')
            is_required = request.form.get('is_required') == 'on'
            
            # Get next sort order
            max_order = db.session.query(db.func.max(ChecklistItem.sort_order)).filter_by(
                checklist_id=checklist_id
            ).scalar() or 0
            
            item = ChecklistItem(
                checklist_id=checklist_id,
                title=title,
                description=description,
                is_required=is_required,
                sort_order=max_order + 1
            )
            
            db.session.add(item)
            db.session.commit()
            flash(f'Document item "{title}" added successfully', 'success')
            
        elif action == 'delete_item':
            item_id = request.form.get('item_id')
            item = ChecklistItem.query.filter_by(
                id=item_id, 
                checklist_id=checklist_id
            ).first()
            if item:
                db.session.delete(item)
                db.session.commit()
                flash('Document item deleted successfully', 'success')
        
        return redirect(url_for('documents.edit_checklist', checklist_id=checklist_id))
    
    return render_template('documents/edit_checklist.html', checklist=checklist)


@documents_bp.route('/checklist-dashboard/<int:checklist_id>')
def checklist_dashboard(checklist_id):
    """Modern dashboard view for a specific checklist"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    return render_template('documents/checklist_dashboard.html', checklist=checklist)


@documents_bp.route('/download-document/<int:document_id>')
def download_document(document_id):
    """Download a client-uploaded document"""
    firm_id = session['firm_id']
    
    # Get document and verify access
    document = ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
        ClientDocument.id == document_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    if not os.path.exists(document.file_path):
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('documents.document_checklists'))
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename,
        mimetype=document.mime_type
    )


@documents_bp.route('/uploaded-documents')
def uploaded_documents():
    """View all uploaded documents across all checklists"""
    firm_id = session['firm_id']
    
    # Get all uploaded documents for this firm
    documents = ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
        Client.firm_id == firm_id
    ).order_by(ClientDocument.uploaded_at.desc()).all()
    
    return render_template('documents/uploaded_documents.html', documents=documents)


@documents_bp.route('/api/checklist-stats/<int:checklist_id>')
def checklist_stats_api(checklist_id):
    """API endpoint for real-time checklist statistics"""
    firm_id = session['firm_id']
    
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    stats = {
        'total_items': len(checklist.items),
        'pending': checklist.pending_items_count,
        'uploaded': checklist.uploaded_items_count,
        'completed': checklist.completed_items_count,
        'progress': checklist.progress_percentage,
        'last_activity': None
    }
    
    # Get last activity
    if checklist.items:
        latest_update = max([item.updated_at for item in checklist.items if item.updated_at])
        if latest_update:
            stats['last_activity'] = latest_update.strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(stats)


@documents_bp.route('/checklist/<int:checklist_id>/share')
def share_checklist(checklist_id):
    """Generate shareable link for public checklist access"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    # Generate or get existing access token
    if not checklist.public_access_token:
        import secrets
        checklist.public_access_token = secrets.token_urlsafe(32)
        checklist.public_access_enabled = True
        db.session.commit()
    
    # Generate shareable URL
    from flask import url_for
    share_url = url_for('documents.public_checklist', token=checklist.public_access_token, _external=True)
    
    return render_template('documents/share_checklist.html', 
                         checklist=checklist, 
                         share_url=share_url)


@documents_bp.route('/checklist/<int:checklist_id>/revoke-share', methods=['POST'])
def revoke_checklist_share(checklist_id):
    """Revoke public access to checklist"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    # Disable public access
    checklist.public_access_enabled = False
    db.session.commit()
    
    flash('Public access revoked successfully', 'success')
    return redirect(url_for('documents.share_checklist', checklist_id=checklist_id))


@documents_bp.route('/checklist/<int:checklist_id>/regenerate-share', methods=['POST'])
def regenerate_checklist_share(checklist_id):
    """Regenerate shareable token for checklist"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    # Generate new token
    import secrets
    checklist.public_access_token = secrets.token_urlsafe(32)
    checklist.public_access_enabled = True
    db.session.commit()
    
    flash('New shareable link generated', 'success')
    return redirect(url_for('documents.share_checklist', checklist_id=checklist_id))


@documents_bp.route('/checklist/<token>')
def public_checklist(token):
    """Public view of checklist for client access"""
    # Find checklist by token
    checklist = DocumentChecklist.query.filter_by(
        public_access_token=token,
        public_access_enabled=True
    ).first_or_404()
    
    return render_template('documents/public_checklist.html', checklist=checklist)


@documents_bp.route('/checklist/<token>/upload', methods=['POST'])
def public_checklist_upload(token):
    """Handle public document upload via shared link"""
    # Find checklist by token
    checklist = DocumentChecklist.query.filter_by(
        public_access_token=token,
        public_access_enabled=True
    ).first_or_404()
    
    item_id = request.form.get('item_id')
    item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first_or_404()
    
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('documents.public_checklist', token=token))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('documents.public_checklist', token=token))
    
    from werkzeug.utils import secure_filename
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create client-specific subdirectory
        from flask import current_app
        client_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'client_{checklist.client_id}')
        os.makedirs(client_upload_dir, exist_ok=True)
        
        file_path = os.path.join(client_upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
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
        
        flash('File uploaded successfully', 'success')
        return redirect(url_for('documents.public_checklist', token=token))
        
    except Exception as e:
        db.session.rollback()
        # Clean up file if database operation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        flash(f'Error uploading file: {str(e)}', 'error')
        return redirect(url_for('documents.public_checklist', token=token))


@documents_bp.route('/checklist/<token>/status', methods=['POST'])
def public_checklist_status(token):
    """Update document status via public link"""
    # Find checklist by token
    checklist = DocumentChecklist.query.filter_by(
        public_access_token=token,
        public_access_enabled=True
    ).first_or_404()
    
    item_id = request.form.get('item_id')
    new_status = request.form.get('status')
    
    if new_status not in ['already_provided', 'not_applicable', 'pending']:
        flash('Invalid status selected', 'error')
        return redirect(url_for('documents.public_checklist', token=token))
    
    item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first_or_404()
    
    try:
        # If changing from uploaded status, remove the uploaded file
        if item.status == 'uploaded' and new_status != 'uploaded':
            existing_doc = ClientDocument.query.filter_by(
                client_id=checklist.client_id,
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
        return redirect(url_for('documents.public_checklist', token=token))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('documents.public_checklist', token=token))