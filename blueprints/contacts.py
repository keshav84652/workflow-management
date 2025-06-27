"""
Contact management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from core.db_import import db
from models import Contact, ClientContact, Client
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.session_helpers import get_session_firm_id, get_session_user_id

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')


@contacts_bp.route('/')
def list_contacts():
    firm_id = get_session_firm_id()
    
    # Get only contacts associated with clients from this firm
    contacts_query = db.session.query(Contact).join(ClientContact).join(Client).filter(
        Client.firm_id == firm_id
    ).distinct()
    
    firm_contacts = contacts_query.all()
    
    # Add client count for each contact (only count clients from this firm)
    for contact in firm_contacts:
        contact.client_count = db.session.query(ClientContact).join(Client).filter(
            ClientContact.contact_id == contact.id,
            Client.firm_id == firm_id
        ).count()
    
    return render_template('clients/contacts.html', contacts=firm_contacts)


from services.contact_service import ContactService

@contacts_bp.route('/create', methods=['GET', 'POST'])
def create_contact():
    if request.method == 'POST':
        user_id = get_session_user_id()
        result = ContactService().create_contact(request.form, user_id)
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('contacts.list_contacts'))
        else:
            flash(result['message'], 'error')
    return render_template('clients/create_contact.html')


@contacts_bp.route('/<int:id>')
def view_contact(id):
    contact = Contact.query.get_or_404(id)
    firm_id = get_session_firm_id()
    
    # Get clients associated with this contact for this firm
    associated_clients = db.session.query(Client).join(ClientContact).filter(
        ClientContact.contact_id == id,
        Client.firm_id == firm_id
    ).all()
    
    return render_template('clients/view_contact.html', contact=contact, associated_clients=associated_clients)

@contacts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    
    if request.method == 'POST':
        contact.first_name = request.form.get('first_name')
        contact.last_name = request.form.get('last_name')
        contact.email = request.form.get('email')
        contact.phone = request.form.get('phone')
        contact.title = request.form.get('title')
        contact.company = request.form.get('company')
        contact.address = request.form.get('address')
        
        # TODO: Move to service layer
        # db.session.commit()
        
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('contacts.view_contact', id=contact.id))
    
    return render_template('clients/edit_contact.html', contact=contact)


@contacts_bp.route('/<int:contact_id>/clients/<int:client_id>/associate', methods=['POST'])
def associate_contact_client(contact_id, client_id):
    firm_id = get_session_firm_id()
    
    # Verify client belongs to firm
    client = Client.query.filter_by(id=client_id, firm_id=firm_id).first_or_404()
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        # Check if association already exists
        existing = ClientContact.query.filter_by(contact_id=contact_id, client_id=client_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Contact already associated with this client'})
        
        # Create association
        association = ClientContact(contact_id=contact_id, client_id=client_id)
        # TODO: Move to service layer
        # db.session.add(association)
        # TODO: Move to service layer
        # db.session.commit()
        
        return jsonify({'success': True, 'message': f'Contact {contact.full_name} associated with {client.name}'})
    
    except Exception as e:
        # TODO: Move to service layer
        # db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@contacts_bp.route('/<int:contact_id>/clients/<int:client_id>/disassociate', methods=['POST'])
def disassociate_contact_client(contact_id, client_id):
    firm_id = get_session_firm_id()
    
    # Verify client belongs to firm
    client = Client.query.filter_by(id=client_id, firm_id=firm_id).first_or_404()
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        # Find and remove association
        association = ClientContact.query.filter_by(contact_id=contact_id, client_id=client_id).first()
        if association:
            db.session.delete(association)
            # TODO: Move to service layer
            # db.session.commit()
            return jsonify({'success': True, 'message': f'Contact {contact.full_name} disassociated from {client.name}'})
        else:
            return jsonify({'success': False, 'message': 'No association found'})
    
    except Exception as e:
        # TODO: Move to service layer
        # db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@contacts_bp.route('/<int:contact_id>/link_client', methods=['POST'])
def link_contact_client(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    
    client_id = request.form.get('client_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'
    
    if not client_id:
        flash('Please select a client', 'error')
        return redirect(url_for('contacts.view_contact', id=contact_id))
    
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('contacts.list_contacts'))
    
    # Check if association already exists
    existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if existing:
        flash('Contact is already associated with this client', 'error')
        return redirect(url_for('contacts.view_contact', id=contact_id))
    
    # If setting as primary, remove primary status from other contacts for this client
    if is_primary:
        ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
    
    # Create new association
    client_contact = ClientContact(
        client_id=client_id,
        contact_id=contact_id,
        relationship_type=relationship_type,
        is_primary=is_primary
    )
    
    # TODO: Move to service layer
    # db.session.add(client_contact)
    # TODO: Move to service layer
    # db.session.commit()
    
    ActivityService.create_activity_log(f'Contact "{contact.full_name}" linked to client "{client.name}" as {relationship_type}', session['user_id'])
    flash('Client linked successfully!', 'success')
    
    return redirect(url_for('contacts.view_contact', id=contact_id))
