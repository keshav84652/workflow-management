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