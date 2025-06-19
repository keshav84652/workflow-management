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
    clients = Client.query.filter_by(firm_id=firm_id).order_by(Client.name.asc()).all()
    return render_template('clients/clients.html', clients=clients)


@clients_bp.route('/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        client = Client(
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
        db.session.add(client)
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Client "{client.name}" created', session['user_id'])
        
        flash('Client created successfully!', 'success')
        return redirect(url_for('clients.list_clients'))
    
    return render_template('clients/create_client.html')


@clients_bp.route('/<int:id>')
def view_client(id):
    client = Client.query.get_or_404(id)
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    projects = Project.query.filter_by(client_id=id).order_by(Project.created_at.desc()).all()
    
    # Get available contacts (not already associated with this client)
    associated_contact_ids = db.session.query(ClientContact.contact_id).filter_by(client_id=id).subquery()
    available_contacts = Contact.query.filter(~Contact.id.in_(associated_contact_ids)).all()
    
    return render_template('clients/view_client.html', client=client, projects=projects, available_contacts=available_contacts)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_client(id):
    client = Client.query.get_or_404(id)
    if client.firm_id \!= session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.contact_person = request.form.get('contact_person')
        client.entity_type = request.form.get('entity_type')
        client.tax_id = request.form.get('tax_id')
        client.notes = request.form.get('notes')
        
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Client "{client.name}" updated', session['user_id'])
        
        flash('Client updated successfully\!', 'success')
        return redirect(url_for('clients.view_client', id=client.id))
    
    return render_template('clients/edit_client.html', client=client)


@clients_bp.route('/<int:id>/delete', methods=['POST'])
def delete_client(id):
    client = Client.query.get_or_404(id)
    
    # Check access permission
    if client.firm_id \!= session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        client_name = client.name
        
        # Get counts for confirmation message
        project_count = Project.query.filter_by(client_id=id).count()
        task_count = Task.query.join(Project).filter_by(client_id=id).count()
        contact_count = len(client.contacts)
        
        # Create activity log before deletion
        create_activity_log(f'Client "{client_name}" deleted (with {project_count} projects, {task_count} tasks, {contact_count} contacts)', session['user_id'])
        
        # Delete all associated projects (which will cascade delete tasks and attachments)
        projects = Project.query.filter_by(client_id=id).all()
        for project in projects:
            # Delete project attachments
            Attachment.query.filter_by(project_id=project.id).delete()
            
            # Delete all tasks and their comments for this project
            tasks = Task.query.filter_by(project_id=project.id).all()
            for task in tasks:
                TaskComment.query.filter_by(task_id=task.id).delete()
                db.session.delete(task)
            
            # Delete the project
            db.session.delete(project)
        
        # Delete any independent tasks for this client
        independent_tasks = Task.query.filter_by(client_id=id, project_id=None).all()
        for task in independent_tasks:
            TaskComment.query.filter_by(task_id=task.id).delete()
            db.session.delete(task)
        
        # Delete client-contact associations
        ClientContact.query.filter_by(client_id=id).delete()
        
        # Delete client attachments
        Attachment.query.filter_by(client_id=id).delete()
        
        # Delete the client itself
        db.session.delete(client)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Client "{client_name}" and all associated data deleted successfully',
            'redirect': '/clients'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting client: {str(e)}'}), 500


@clients_bp.route('/<int:id>/mark_inactive', methods=['POST'])
def mark_client_inactive(id):
    client = Client.query.get_or_404(id)
    
    # Check access permission
    if client.firm_id \!= session['firm_id']:
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
EOF < /dev/null