"""
Contact management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from core import db
from models import Contact, ClientContact, Client

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')


@contacts_bp.route('/')
def list_contacts():
    firm_id = session['firm_id']
    
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


@contacts_bp.route('/create', methods=['GET', 'POST'])
def create_contact():
    if request.method == 'POST':
        contact = Contact(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            title=request.form.get('title'),
            company=request.form.get('company'),
            address=request.form.get('address')
        )
        
        db.session.add(contact)
        db.session.commit()
        
        flash('Contact created successfully!', 'success')
        return redirect(url_for('contacts.list_contacts'))
    
    return render_template('clients/create_contact.html')


@contacts_bp.route('/<int:id>')
def view_contact(id):
    contact = Contact.query.get_or_404(id)
    firm_id = session['firm_id']
    
    # Get clients associated with this contact for this firm
    associated_clients = db.session.query(Client).join(ClientContact).filter(
        ClientContact.contact_id == id,
        Client.firm_id == firm_id
    ).all()
    
    return render_template('clients/view_contact.html', contact=contact, associated_clients=associated_clients)