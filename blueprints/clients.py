"""
Client management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from services.client_service import ClientService
from utils.session_helpers import get_session_firm_id, get_session_user_id

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')


@clients_bp.route('/')
def list_clients():
    firm_id = get_session_firm_id()
    clients = ClientService.get_clients_for_firm(firm_id)
    return render_template('clients/clients.html', clients=clients)


@clients_bp.route('/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        firm_id = get_session_firm_id()
        user_id = get_session_user_id()
        result = ClientService.create_client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person'),
            entity_type=request.form.get('entity_type', 'Individual'),
            tax_id=request.form.get('tax_id'),
            notes=request.form.get('notes'),
            firm_id=firm_id,
            user_id=user_id
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
    firm_id = get_session_firm_id()
    
    result = ClientService.get_client_with_projects_and_contacts(id, firm_id)
    if not result['success']:
        flash(result['message'], 'error')
        return redirect(url_for('clients.list_clients'))
    
    return render_template('clients/view_client.html', 
                         client=result['client'], 
                         projects=result['projects'], 
                         available_contacts=result['available_contacts'])

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_client(id):
    firm_id = get_session_firm_id()
    
    client = ClientService.get_client_by_id(id, firm_id)
    if not client:
        flash('Client not found or access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    if request.method == 'POST':
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
            firm_id=firm_id,
            user_id=user_id
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
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    result = ClientService.delete_client(id, firm_id, user_id=user_id)
    
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
    user_id = get_session_user_id()
    result = ClientService.toggle_client_status(id, user_id=user_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message'],
            'new_status': result['new_status'],
            'is_active': result['is_active']
        })
    else:
        status_code = 403 if 'access' in result['message'].lower() else 500
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@clients_bp.route('/<int:client_id>/associate_contact', methods=['POST'])
def associate_client_contact(client_id):
    contact_id = request.form.get('contact_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'
    
    if not contact_id:
        flash('Please select a contact', 'error')
        return redirect(url_for('clients.view_client', id=client_id))
    
    user_id = get_session_user_id()
    result = ClientService.associate_contact(
        client_id=client_id,
        contact_id=int(contact_id),
        relationship_type=relationship_type,
        is_primary=is_primary,
        user_id=user_id
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('clients.view_client', id=client_id))


@clients_bp.route('/<int:client_id>/access-setup', methods=['GET', 'POST'])
def client_access_setup(client_id):
    """Set up client portal access for a client"""
    
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create':
            email = request.form.get('email')
            result = ClientService.create_client_portal_user(client_id, email)
            
        elif action == 'regenerate':
            result = ClientService.regenerate_client_access_code(client_id)
            
        elif action == 'toggle':
            result = ClientService.toggle_client_portal_status(client_id)
        
        else:
            result = {'success': False, 'message': 'Invalid action'}
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('clients.client_access_setup', client_id=client_id))
    
    # GET request - get client and portal info
    portal_info = ClientService.get_client_portal_info(client_id)
    if not portal_info['success']:
        flash(portal_info['message'], 'error')
        return redirect(url_for('clients.list_clients'))
    
    return render_template('clients/client_access_setup.html', 
                         client=portal_info['client'], 
                         client_user=portal_info['client_user'])
