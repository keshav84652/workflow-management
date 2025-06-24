"""
Client management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from core import db
from models import Client, Project, Task, User, Contact, ClientContact, ClientUser, ActivityLog, Contact, ClientContact, Attachment, TaskComment
from utils import create_activity_log

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')


@clients_bp.route('/')
def list_clients():
    firm_id = session['firm_id']
    # Use service layer to get clients
    from services.client_service import ClientService
    clients = ClientService.get_clients_for_firm(firm_id)
    return render_template('clients/clients.html', clients=clients)


@clients_bp.route('/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        # Use service layer to create client
        result = ClientService.create_client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person'),
            entity_type=request.form.get('entity_type', 'Individual'),
            tax_id=request.form.get('tax_id'),
            notes=request.form.get('notes'),
            firm_id=firm_id
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('clients.list_clients'))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('clients.create_client'))
    
    return render_template('clients/create_client.html')


@clients_bp.route('/<int:id>')
def view_client(id):
    firm_id = session['firm_id']
    
    # Use service layer to get client
    client = ClientService.get_client_by_id(id, firm_id)
    if not client:
        flash('Client not found or access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    projects = Project.query.filter_by(client_id=id).order_by(Project.created_at.desc()).all()
    
    # Get available contacts (not already associated with this client)
    associated_contact_ids = db.session.query(ClientContact.contact_id).filter_by(client_id=id).subquery()
    available_contacts = Contact.query.filter(~Contact.id.in_(associated_contact_ids)).all()
    
    return render_template('clients/view_client.html', client=client, projects=projects, available_contacts=available_contacts)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_client(id):
    firm_id = session['firm_id']
    
    # Use service layer to get client
    from services.client_service import ClientService
    client = ClientService.get_client_by_id(id, firm_id)
    if not client:
        flash('Client not found or access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    if request.method == 'POST':
        # Use service layer to update client
        result = ClientService.update_client(
            client_id=id,
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person'),
            entity_type=request.form.get('entity_type'),
            tax_id=request.form.get('tax_id'),
            notes=request.form.get('notes'),
            firm_id=firm_id
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('clients.view_client', id=id))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('clients.edit_client', id=id))
    
    return render_template('clients/edit_client.html', client=client)


@clients_bp.route('/<int:id>/delete', methods=['POST'])
def delete_client(id):
    firm_id = session['firm_id']
    
    # Use service layer to delete client
    result = ClientService.delete_client(id, firm_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message'],
            'redirect': url_for('clients.list_clients')
        })
    else:
        status_code = 403 if 'access' in result['message'].lower() else 500
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@clients_bp.route('/<int:id>/mark_inactive', methods=['POST'])
def mark_client_inactive(id):
    client = Client.query.get_or_404(id)
    
    # Check access permission
    if client.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        client_name = client.name
        previous_status = "Active" if client.is_active else "Inactive"
        
        # Toggle active status
        client.is_active = not client.is_active
        new_status = "Active" if client.is_active else "Inactive"
        
        # Update all associated projects to match client status
        projects = Project.query.filter_by(client_id=id).all()
        for project in projects:
            if client.is_active:
                # If activating client, set projects to Active if they were inactive
                if project.status in ['Inactive', 'On Hold']:
                    project.status = 'Active'
            else:
                # If deactivating client, set active projects to On Hold
                if project.status == 'Active':
                    project.status = 'On Hold'
        
        db.session.commit()
        
        # Create activity log
        action = f'Client "{client_name}" marked as {new_status} (was {previous_status})'
        if not client.is_active:
            action += f' - {len(projects)} projects set to On Hold'
        else:
            action += f' - {len(projects)} projects reactivated'
        
        create_activity_log(action, session['user_id'])
        
        return jsonify({
            'success': True, 
            'message': f'Client "{client_name}" marked as {new_status}',
            'new_status': new_status,
            'is_active': client.is_active
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating client status: {str(e)}'}), 500


@clients_bp.route('/<int:client_id>/associate_contact', methods=['POST'])
def associate_client_contact(client_id):
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    contact_id = request.form.get('contact_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'
    
    if not contact_id:
        flash('Please select a contact', 'error')
        return redirect(url_for('clients.view_client', id=client_id))
    
    # Check if association already exists
    existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if existing:
        flash('Contact is already associated with this client', 'error')
        return redirect(url_for('clients.view_client', id=client_id))
    
    # If setting as primary, remove primary status from other contacts
    if is_primary:
        ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
    
    # Create new association
    client_contact = ClientContact(
        client_id=client_id,
        contact_id=contact_id,
        relationship_type=relationship_type,
        is_primary=is_primary
    )
    
    db.session.add(client_contact)
    db.session.commit()
    
    contact = Contact.query.get(contact_id)
    create_activity_log(f'Contact "{contact.full_name}" linked to client "{client.name}" as {relationship_type}', session['user_id'])
    flash('Contact linked successfully!', 'success')
    
    return redirect(url_for('clients.view_client', id=client_id))


@clients_bp.route('/<int:client_id>/access-setup', methods=['GET', 'POST'])
def client_access_setup(client_id):
    """Set up client portal access for a client"""
    firm_id = session['firm_id']
    
    # Verify client belongs to this firm
    client = Client.query.filter_by(id=client_id, firm_id=firm_id).first_or_404()
    
    # Check if client user already exists
    client_user = ClientUser.query.filter_by(client_id=client_id).first()
    
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create' and not client_user:
            # Create new client user
            email = request.form.get('email') or client.email
            
            # Ensure we have an email (use client email as fallback)
            if not email:
                flash('Client must have an email address to create portal access. Please update client information first.', 'error')
                return redirect(url_for('clients.client_access_setup', client_id=client_id))
            
            client_user = ClientUser(
                client_id=client_id,
                email=email,
                is_active=True
            )
            # Generate 8-character access code
            client_user.generate_access_code()
            
            db.session.add(client_user)
            db.session.commit()
            
            flash(f'Client portal access created successfully! Access code: {client_user.access_code}', 'success')
            
        elif action == 'regenerate' and client_user:
            # Regenerate access code
            old_code = client_user.access_code
            client_user.generate_access_code()
            db.session.commit()
            
            flash(f'New access code generated: {client_user.access_code}', 'success')
            
        elif action == 'toggle' and client_user:
            # Toggle active status
            client_user.is_active = not client_user.is_active
            db.session.commit()
            
            status = 'activated' if client_user.is_active else 'deactivated'
            flash(f'Client portal access {status}', 'success')
        
        # Refresh client_user object after changes
        if client_user:
            db.session.refresh(client_user)
    
    return render_template('clients/client_access_setup.html', client=client, client_user=client_user)
