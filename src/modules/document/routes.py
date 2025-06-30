"""
Document and checklist management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.utils.consolidated import get_session_firm_id, get_session_user_id
from .service import DocumentService

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/checklists')
@documents_bp.route('/document_checklists')  # Legacy URL support
def document_checklists():
    """CPA view to manage document checklists"""
    firm_id = get_session_firm_id()
    
    # Get data using service layer
    document_service = DocumentService()
    checklists = document_service.get_checklists_for_firm(firm_id)
    clients = document_service.get_clients_for_firm(firm_id)
    
    return render_template('documents/document_checklists.html', checklists=checklists, clients=clients)


@documents_bp.route('/create-checklist', methods=['GET', 'POST'])
def create_checklist():
    """Create a new document checklist"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name')
        description = request.form.get('description', '')
        user_id = get_session_user_id()
        
        # Use service layer for business logic
        result = document_service.create_checklist(
            name=name,
            description=description,
            client_id=client_id,
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
    clients = document_service.get_clients_for_firm(firm_id)
    return render_template('documents/create_checklist_modern.html', clients=clients)


@documents_bp.route('/edit-checklist/<int:checklist_id>', methods=['GET', 'POST'])
def edit_checklist(checklist_id):
    """Edit a document checklist and its items"""
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    document_service = DocumentService()
    
    # Get checklist using service layer
    checklist = document_service.get_checklist_by_id(checklist_id, firm_id)
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
            result = document_service.update_checklist_with_items(
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
            
            result = document_service.update_checklist(
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
            
            result = document_service.add_checklist_item(
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
            
            result = document_service.delete_checklist_item(
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
    
    document_service = DocumentService()
    
    # Get checklist using service layer
    checklist = document_service.get_checklist_by_id(checklist_id, firm_id)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    return render_template('documents/checklist_dashboard.html', checklist=checklist)


@documents_bp.route('/download-document/<int:document_id>')
def download_document(document_id):
    """Download a client-uploaded document"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    
    # Get document using service layer
    document = document_service.get_document_for_download(document_id, firm_id)
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
    
    document_service = DocumentService()
    
    # Get client and verify access using service layer
    client = document_service.get_client_by_id_and_firm(client_id, firm_id)
    if not client:
        flash('Client not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    # Get all checklists and documents for this client
    checklists = document_service.get_checklists_by_client_and_firm(client_id, firm_id)
    
    return render_template('documents/document_analysis.html', 
                         client=client, 
                         checklists=checklists)


@documents_bp.route('/uploaded-documents')
def uploaded_documents():
    """View all uploaded documents across all checklists"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    
    # Get all uploaded documents for this firm using service layer
    documents = document_service.get_uploaded_documents(firm_id)
    
    return render_template('documents/uploaded_documents.html', documents=documents)


@documents_bp.route('/api/checklist-stats/<int:checklist_id>')
def checklist_stats_api(checklist_id):
    """API endpoint for real-time checklist statistics"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    checklist = document_service.get_checklist_by_id(checklist_id, firm_id)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
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
    
    document_service = DocumentService()
    checklist = document_service.generate_share_token(checklist_id, firm_id)
    from flask import url_for
    share_url = url_for('documents.public_checklist', token=checklist.public_access_token, _external=True)
    return render_template('documents/share_checklist.html',
                         checklist=checklist,
                         share_url=share_url)


@documents_bp.route('/checklist/<int:checklist_id>/revoke-share', methods=['POST'])
def revoke_checklist_share(checklist_id):
    """Revoke public access to checklist"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    document_service.revoke_share(checklist_id, firm_id)
    flash('Public access revoked successfully', 'success')
    return redirect(url_for('documents.share_checklist', checklist_id=checklist_id))


@documents_bp.route('/checklist/<int:checklist_id>/regenerate-share', methods=['POST'])
def regenerate_checklist_share(checklist_id):
    """Regenerate shareable token for checklist"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    document_service.regenerate_share_token(checklist_id, firm_id)
    flash('New shareable link generated', 'success')
    return redirect(url_for('documents.share_checklist', checklist_id=checklist_id))


@documents_bp.route('/checklist/<token>')
def public_checklist(token):
    """Public view of checklist for client access"""
    document_service = DocumentService()
    
    # Find checklist by token using service layer
    checklist = document_service.get_checklist_by_token(token)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    return render_template('documents/public_checklist.html', checklist=checklist)


@documents_bp.route('/checklist/<token>/upload', methods=['POST'])
def public_checklist_upload(token):
    """Handle public document upload via shared link"""
    document_service = DocumentService()
    
    # Find checklist by token using service layer
    checklist = document_service.get_checklist_by_token(token)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    item_id = request.form.get('item_id')
    file = request.files.get('file')
    
    # Use service layer for file upload business logic
    result = document_service.upload_file_to_checklist_item(
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
    document_service = DocumentService()
    
    # Find checklist by token using service layer
    checklist = document_service.get_checklist_by_token(token)
    if not checklist:
        flash('Checklist not found or access denied', 'error')
        return redirect(url_for('documents.document_checklists'))
    
    item_id = request.form.get('item_id')
    new_status = request.form.get('status')
    
    result = document_service.update_checklist_item_status(token, item_id, new_status)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('documents.public_checklist', token=token))

@documents_bp.route("/api/checklists/refresh")
def refresh_checklists_data():
    """API endpoint to get refreshed checklist data"""
    firm_id = get_session_firm_id()
    
    document_service = DocumentService()
    
    # Get all checklists for the firm using service layer
    checklists = document_service.get_active_checklists_with_client_filter(firm_id)
    
    # Get all clients for the firm using service layer
    clients = document_service.get_clients_for_firm(firm_id)
    
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

