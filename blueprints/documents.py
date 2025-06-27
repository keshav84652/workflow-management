"""
Document and checklist management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

from core.db_import import db
from models import (
    DocumentChecklist, ChecklistItem, ClientDocument, 
    ClientUser, Attachment, User, ClientChecklistAccess
)
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.consolidated import get_session_firm_id, get_session_user_id
from services.document_service import DocumentService

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/checklists')
@documents_bp.route('/document_checklists')  # Legacy URL support
def document_checklists():
    """CPA view to manage document checklists"""
    firm_id = get_session_firm_id()
    
    # Get data using service layer
    checklists = DocumentService.get_checklists_for_firm(firm_id)
    clients = DocumentService.get_clients_for_firm(firm_id)
    
    return render_template('documents/document_checklists.html', checklists=checklists, clients=clients)


@documents_bp.route('/create-checklist', methods=['GET', 'POST'])
def create_checklist():
    """Create a new document checklist"""
    firm_id = get_session_firm_id()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name')
        description = request.form.get('description', '')
        user_id = get_session_user_id()
        
        # Use service layer for business logic
        result = DocumentService.create_checklist(
            client_id=client_id,
            name=name,
            description=description,
            firm_id=firm_id,
            user_id=user_id
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('documents.edit_checklist', checklist_id=result['checklist'].id))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('documents.document_checklists'))
    
    # GET request - show form
    clients = DocumentService.get_clients_for_firm(firm_id)
    return render_template('documents/create_checklist_modern.html', clients=clients)


@documents_bp.route('/edit-checklist/<int:checklist_id>', methods=['GET', 'POST'])
def edit_checklist(checklist_id):
    """Edit a document checklist and its items"""
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    # Get checklist using service layer
    checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # If no specific action, this is the main form submission (Save Changes button)
        if not action:
            name = request.form.get('name')
            description = request.form.get('description', '')
            
            # Prepare items data for service
            items_data = {
                'deleted_item_ids': request.form.getlist('deleted_item_ids[]'),
                'item_ids': request.form.getlist('item_ids[]'),
                'item_titles': request.form.getlist('item_titles[]'),
                'item_descriptions': request.form.getlist('item_descriptions[]'),
                'item_required': request.form.getlist('item_required[]'),
                'item_sort_orders': request.form.getlist('item_sort_orders[]')
            }
            
            # Use service layer for complex update
            result = DocumentService.update_checklist_with_items(
                checklist_id=checklist_id,
                name=name,
                description=description,
                items_data=items_data,
                firm_id=firm_id,
                user_id=user_id
            )
            
            flash(result['message'], 'success' if result['success'] else 'error')
            return redirect(url_for('documents.edit_checklist', checklist_id=checklist_id))
        
        elif action == 'update_checklist':
            name = request.form.get('name')
            description = request.form.get('description', '')
            
            result = DocumentService.update_checklist(
                checklist_id=checklist_id,
                name=name,
                description=description,
                firm_id=firm_id,
                user_id=user_id
            )
            
            flash(result['message'], 'success' if result['success'] else 'error')
            
        elif action == 'add_item':
            title = request.form.get('title')
            description = request.form.get('description', '')
            is_required = request.form.get('is_required') == 'on'
            
            result = DocumentService.add_checklist_item(
                checklist_id=checklist_id,
                item_name=title,
                description=description,
                is_required=is_required,
                firm_id=firm_id,
                user_id=user_id
            )
            
            flash(result['message'], 'success' if result['success'] else 'error')
            
        elif action == 'delete_item':
            item_id = request.form.get('item_id')
            
            result = DocumentService.delete_checklist_item(
                item_id=item_id,
                checklist_id=checklist_id,
                firm_id=firm_id,
                user_id=user_id
            )
            
            flash(result['message'], 'success' if result['success'] else 'error')
        
        return redirect(url_for('documents.edit_checklist', checklist_id=checklist_id))
    
    return render_template('documents/edit_checklist.html', checklist=checklist)


@documents_bp.route('/checklist-dashboard/<int:checklist_id>')
def checklist_dashboard(checklist_id):
    """Modern dashboard view for a specific checklist"""
    firm_id = get_session_firm_id()
    
    # Get checklist using service layer
    checklist = DocumentService.get_checklist_by_id(checklist_id, firm_id)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    return render_template('documents/checklist_dashboard.html', checklist=checklist)


@documents_bp.route('/download-document/<int:document_id>')
def download_document(document_id):
    """Download a client-uploaded document"""
    firm_id = get_session_firm_id()
    
    # Get document using service layer
    document = DocumentService.get_document_for_download(document_id, firm_id)
    if not document:
        flash('Document not found or access denied', 'error')
        return redirect(request.referrer or url_for('documents.document_checklists'))
    
    if not os.path.exists(document.file_path):
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('documents.document_checklists'))
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename,
        mimetype=document.mime_type
    )


@documents_bp.route('/analysis/<int:client_id>')
def view_document_analysis(client_id):
    """View document analysis for a client"""
    firm_id = get_session_firm_id()
    
    # Get client and verify access
    client = Client.query.filter_by(id=client_id, firm_id=firm_id).first_or_404()
    
    # Get all checklists and documents for this client
    checklists = DocumentChecklist.query.filter_by(
        client_id=client_id, 
        firm_id=firm_id
    ).all()
    
    return render_template('documents/document_analysis.html', 
                         client=client, 
                         checklists=checklists)


@documents_bp.route('/uploaded-documents')
def uploaded_documents():
    """View all uploaded documents across all checklists"""
    firm_id = get_session_firm_id()
    
    # Get all uploaded documents for this firm using service layer
    documents = DocumentService.get_uploaded_documents(firm_id)
    
    return render_template('documents/uploaded_documents.html', documents=documents)


@documents_bp.route('/api/checklist-stats/<int:checklist_id>')
def checklist_stats_api(checklist_id):
    """API endpoint for real-time checklist statistics"""
    firm_id = get_session_firm_id()
    
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
    firm_id = get_session_firm_id()
    checklist = DocumentService.generate_share_token(checklist_id, firm_id)
    from flask import url_for
    share_url = url_for('documents.public_checklist', token=checklist.public_access_token, _external=True)
    return render_template('documents/share_checklist.html',
                         checklist=checklist,
                         share_url=share_url)


@documents_bp.route('/checklist/<int:checklist_id>/revoke-share', methods=['POST'])
def revoke_checklist_share(checklist_id):
    """Revoke public access to checklist"""
    firm_id = get_session_firm_id()
    DocumentService.revoke_share(checklist_id, firm_id)
    flash('Public access revoked successfully', 'success')
    return redirect(url_for('documents.share_checklist', checklist_id=checklist_id))


@documents_bp.route('/checklist/<int:checklist_id>/regenerate-share', methods=['POST'])
def regenerate_checklist_share(checklist_id):
    """Regenerate shareable token for checklist"""
    firm_id = get_session_firm_id()
    DocumentService.regenerate_share_token(checklist_id, firm_id)
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
    file = request.files.get('file')
    
    # Use service layer for file upload business logic
    result = DocumentService.upload_file_to_checklist_item(
        file=file,
        token=token,
        item_id=int(item_id) if item_id else None
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
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
    
    result = DocumentService.update_checklist_item_status(token, item_id, new_status)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('documents.public_checklist', token=token))

@documents_bp.route("/api/checklists/refresh")
def refresh_checklists_data():
    """API endpoint to get refreshed checklist data"""
    firm_id = get_session_firm_id()
    
    # Get all checklists for the firm
    checklists = DocumentChecklist.query.join(Client).filter(
        Client.firm_id == firm_id,
        DocumentChecklist.is_active == True
    ).order_by(DocumentChecklist.created_at.desc()).all()
    
    # Get all clients for the firm
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    # Calculate clients with access
    clients_with_access = [c for c in clients if any(
        checklist.public_access_enabled for checklist in c.document_checklists
    )]
    
    # Prepare data for JSON response
    data = {
        "stats": {
            "active_checklists": len(checklists),
            "total_clients": len(clients),
            "portal_access": len(clients_with_access),
            "total_documents": sum(len(checklist.items) for checklist in checklists)
        },
        "checklists": []
    }
    
    for checklist in checklists:
        completed_items = sum(1 for item in checklist.items if item.client_documents)
        total_items = len(checklist.items)
        completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0
        
        data["checklists"].append({
            "id": checklist.id,
            "client_name": checklist.client.name,
            "name": checklist.name,
            "description": checklist.description,
            "completion_rate": round(completion_rate),
            "completed_items": completed_items,
            "total_items": total_items,
            "public_access_enabled": checklist.public_access_enabled,
            "view_url": url_for("documents.checklist_dashboard", checklist_id=checklist.id),
            "edit_url": url_for("documents.edit_checklist", checklist_id=checklist.id)
        })
    
    return jsonify(data)

