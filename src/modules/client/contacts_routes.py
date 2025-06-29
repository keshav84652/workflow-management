"""
Contact management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from core.db_import import db
from src.models import Contact, ClientContact, Client
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.consolidated import get_session_firm_id, get_session_user_id

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')


@contacts_bp.route('/')
def list_contacts():
    firm_id = get_session_firm_id()
    contact_service = ContactService()
    firm_contacts = contact_service.list_contacts(firm_id)
    return render_template('clients/contacts.html', contacts=firm_contacts)


from .contact_service import ContactService

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
    firm_id = get_session_firm_id()
    contact_service = ContactService()
    result = contact_service.view_contact(id, firm_id)
    return render_template('clients/view_contact.html', contact=result['contact'], associated_clients=result['associated_clients'])

@contacts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_contact(id):
    user_id = get_session_user_id()
    if request.method == 'POST':
        result = ContactService().update_contact(id, request.form, user_id)
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('contacts.view_contact', id=id))
        else:
            flash(result['message'], 'error')
    contact_service = ContactService()
    result = contact_service.view_contact(id, get_session_firm_id())
    return render_template('clients/edit_contact.html', contact=result['contact'])


@contacts_bp.route('/<int:contact_id>/clients/<int:client_id>/associate', methods=['POST'])
def associate_contact_client(contact_id, client_id):
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    result = ContactService().associate_contact_with_client(contact_id, client_id, firm_id, user_id)
    return jsonify(result)


@contacts_bp.route('/<int:contact_id>/clients/<int:client_id>/disassociate', methods=['POST'])
def disassociate_contact_client(contact_id, client_id):
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    result = ContactService().disassociate_contact_from_client(contact_id, client_id, firm_id, user_id)
    return jsonify(result)


@contacts_bp.route('/<int:contact_id>/link_client', methods=['POST'])
def link_contact_client(contact_id):
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    client_id = request.form.get('client_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'

    if not client_id:
        flash('Please select a client', 'error')
        return redirect(url_for('contacts.view_contact', id=contact_id))

    result = ContactService().link_contact_to_client(
        contact_id=contact_id,
        client_id=client_id,
        relationship_type=relationship_type,
        is_primary=is_primary,
        firm_id=firm_id,
        user_id=user_id
    )
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('contacts.view_contact', id=contact_id))
